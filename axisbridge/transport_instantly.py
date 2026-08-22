"""
Instantly (api.instantly.ai) send transport.

    ############################################################################
    # ENDPOINT SHAPES ARE RECONSTRUCTED, NOT VERIFIED AGAINST LIVE DOCS.       #
    #                                                                          #
    # developer.instantly.ai is egress-blocked in the environment that wrote  #
    # this file — WebFetch to it returned EGRESS_BLOCKED. Everything below     #
    # comes from WebSearch snippets of Instantly's own changelog and help      #
    # articles, which is a lower confidence source than reading the docs.      #
    # Field names believed correct: eaccount, to_address, subject, body        #
    # {html,text}, campaign_id (nullable), reply_to_uuid. Auth: Bearer token.  #
    #                                                                          #
    # verify_connection() below makes ONE real, harmless GET call before any   #
    # send is attempted. If a field name here is wrong, that call — or the     #
    # first real send, which logs the full raw response body on any non-2xx —  #
    # will show it immediately instead of failing silently mid-batch.          #
    # CONFIRM against https://developer.instantly.ai/api/v2/email before the   #
    # first live batch.                                                       #
    ############################################################################

Ownership split, deliberate: THIS pipeline owns sequencing (day offsets, the claims
gate, the four-slot scarcity gate, reply/thread linkage). Instantly is used purely as a
send transport for an already-fully-rendered, already-gated message — never as its own
campaign automation. Uploading leads into an Instantly campaign and letting Instantly's
own step engine fire them would bypass every gate this repository enforces per-step.
"""
from __future__ import annotations
import argparse, csv, json, logging, os, pathlib, subprocess, sys, time
from datetime import datetime, timezone

import requests

log = logging.getLogger("transport_instantly")

API_BASE = "https://api.instantly.ai/api/v2"
API_KEY_ENV = "INSTANTLY_API_KEY"

# Which mailbox sends for which sequence. SEQUENCE_6 is specified to use "a different
# sending domain/inbox than their first pass" — so it gets its own env var rather than
# falling back to the default silently.
EACCOUNT_ENV = {"_default": "AXISBRIDGE_INSTANTLY_EACCOUNT",
                 "SEQUENCE_6": "AXISBRIDGE_INSTANTLY_EACCOUNT_SEQ6"}

THREAD_STORE = pathlib.Path("data/instantly_threads.json")
SEND_LOG = pathlib.Path("data/send_log.jsonl")
LEDGER = pathlib.Path("metrics/ledger.csv")
SENT_DIR_NAME = "sent"

MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class ConnectGateError(Exception):
    """Raised when a required credential is missing. This IS the §1.1 Connect gate."""


class TransportError(Exception):
    pass


def _api_key() -> str:
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        raise ConnectGateError(
            f"{API_KEY_ENV} is not set. Generate it in Instantly under Settings > API "
            f"(v2 key — v1 keys were deprecated and are not compatible) and export it as "
            f"an environment variable. Never paste it into a chat, a commit, or this file."
        )
    return key


def resolve_eaccount(sequence: str) -> str:
    env_name = EACCOUNT_ENV.get(sequence, EACCOUNT_ENV["_default"])
    val = os.environ.get(env_name, "").strip()
    if not val:
        raise ConnectGateError(
            f"{env_name} is not set — no Instantly sending mailbox configured for "
            f"{sequence}. Set it to the exact email address of a mailbox already "
            f"connected in your Instantly workspace."
        )
    return val


class InstantlyClient:
    def __init__(self, api_key: str | None = None, base_url: str = API_BASE, timeout: int = 30):
        self.key = api_key or _api_key()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _call(self, method: str, path: str, **kw) -> dict:
        url = f"{self.base_url}{path}"
        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = self.session.request(method, url, timeout=self.timeout, **kw)
            except requests.RequestException as e:
                last_exc = e
                log.warning("network error on %s %s (attempt %d/%d): %s", method, path, attempt, MAX_RETRIES, e)
                time.sleep(2 ** attempt)
                continue
            if r.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                log.warning("HTTP %d on %s %s (attempt %d/%d) — retrying: %s",
                           r.status_code, method, path, attempt, MAX_RETRIES, r.text[:300])
                time.sleep(2 ** attempt)
                continue
            if not r.ok:
                # Full raw body logged, not swallowed — this is how a wrong field name surfaces.
                raise TransportError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:1000]}")
            return r.json() if r.content else {}
        raise TransportError(f"{method} {path} failed after {MAX_RETRIES} attempts: {last_exc}")

    def list_accounts(self) -> list[dict]:
        data = self._call("GET", "/accounts", params={"limit": 100})
        return data.get("items", data if isinstance(data, list) else [])

    def send_new(self, *, eaccount: str, to_address: str, subject: str, text: str, html: str) -> dict:
        payload = {"eaccount": eaccount, "to_address": to_address, "subject": subject,
                   "body": {"text": text, "html": html}, "campaign_id": None}
        return self._call("POST", "/emails", json=payload)

    def send_reply(self, *, eaccount: str, reply_to_uuid: str, subject: str, text: str, html: str) -> dict:
        payload = {"eaccount": eaccount, "reply_to_uuid": reply_to_uuid, "subject": subject,
                   "body": {"text": text, "html": html}}
        return self._call("POST", "/emails/reply", json=payload)


def verify_connection() -> dict:
    """One real, harmless GET. Run this before any batch — see module docstring."""
    client = InstantlyClient()
    accounts = client.list_accounts()
    log.info("Instantly connection OK — %d mailbox(es) visible to this API key", len(accounts))
    for a in accounts:
        log.info("  %s", a.get("email", a))
    return {"ok": True, "accounts": accounts}


# --------------------------------------------------------------------- rendering
def _to_html(text: str) -> str:
    """Minimal, escaped plain-text -> HTML. The templates are plain text; this is not
    a markdown renderer, just enough structure that the HTML part isn't unreadable."""
    import html as _html
    esc = _html.escape(text)
    paras = esc.split("\n\n")
    return "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paras if p.strip())


# --------------------------------------------------------------------- thread state
def _load_threads() -> dict:
    return json.loads(THREAD_STORE.read_text()) if THREAD_STORE.exists() else {}


def _save_threads(d: dict) -> None:
    THREAD_STORE.parent.mkdir(parents=True, exist_ok=True)
    THREAD_STORE.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")


def _thread_key(artifact: dict) -> str:
    return f"{artifact['prospect_id']}:{artifact['sequence']}"


# --------------------------------------------------------------------- ledger
def _append_ledger(prospect_id: str, note: str) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    is_new = not LEDGER.exists() or LEDGER.stat().st_size == 0
    with LEDGER.open("a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["event_id", "ts", "prospect_id", "stage", "amount_gbp", "cost_gbp", "fulfilment_hours", "note"])
        # event_id: count existing data rows (works whether or not header was just written)
        with LEDGER.open() as rf:
            n = sum(1 for _ in rf) - 1
        w.writerow([n, datetime.now(timezone.utc).isoformat(timespec="seconds"), prospect_id,
                   "contacted", "", 0, "", note])


def _log_send(record: dict) -> None:
    SEND_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SEND_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


# --------------------------------------------------------------------- batch send
def run_presend_gate(outbox: pathlib.Path) -> None:
    """Re-run the JS pre-send gate immediately before a real send — the outbox may have
    been edited, or time may have passed and new suppressions added, since it last ran."""
    result = subprocess.run(
        ["node", "system/outbound/presend.mjs", "--outbox", str(outbox)],
        capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        raise TransportError(
            "Pre-send gate failed — see output above. Refusing to send anything. "
            "This check runs immediately before transmission, not just once at build time.")


def send_batch(outbox: pathlib.Path, *, dry_run: bool = True, limit: int | None = None,
               skip_gate: bool = False) -> dict:
    if not dry_run and not skip_gate:
        run_presend_gate(outbox)

    client = None if dry_run else InstantlyClient()
    threads = _load_threads()
    sent_dir = outbox / SENT_DIR_NAME
    files = sorted(outbox.glob("*.json"), key=lambda p: p.name)   # stable order: step 1 before step 2+

    sent, skipped, failed = [], [], []
    for f in files:
        if limit is not None and len(sent) >= limit:
            break
        artifact = json.loads(f.read_text())
        key = _thread_key(artifact)
        try:
            eaccount = resolve_eaccount(artifact["sequence"])
        except ConnectGateError as e:
            skipped.append((f.name, str(e))); continue

        if artifact.get("reply_in_thread"):
            th = threads.get(key)
            if not th:
                skipped.append((f.name, f"no prior thread recorded for {key} — cannot reply into a "
                                        f"thread that was never started. Send step 1 first."))
                continue
        else:
            th = None

        if dry_run:
            log.info("[DRY RUN] would send %s: %s -> %s (%s)", f.name, eaccount, artifact["to"],
                     "reply" if th else "new")
            sent.append(f.name)
            continue

        text = artifact["body"]
        html = _to_html(text)
        try:
            if th:
                resp = client.send_reply(eaccount=eaccount, reply_to_uuid=th["email_id"],
                                         subject=th.get("subject", artifact.get("subject") or ""),
                                         text=text, html=html)
            else:
                resp = client.send_new(eaccount=eaccount, to_address=artifact["to"],
                                       subject=artifact["subject"], text=text, html=html)
        except TransportError as e:
            failed.append((f.name, str(e)))
            _log_send({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      "file": f.name, "prospect_id": artifact["prospect_id"], "ok": False, "error": str(e)})
            continue

        email_id = resp.get("id") or resp.get("email_id")
        if not th:
            threads[key] = {"email_id": email_id, "subject": artifact["subject"], "eaccount": eaccount}
            _save_threads(threads)

        _append_ledger(artifact["prospect_id"], f"{artifact['sequence']}.{artifact['step']} sent via Instantly")
        _log_send({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "file": f.name,
                  "prospect_id": artifact["prospect_id"], "ok": True, "instantly_id": email_id})
        sent_dir.mkdir(exist_ok=True)
        f.rename(sent_dir / f.name)          # moved, not deleted — never re-sent, always inspectable
        sent.append(f.name)

    return {"sent": sent, "skipped": skipped, "failed": failed, "dry_run": dry_run}


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--outbox", type=pathlib.Path, default=pathlib.Path("outbox"))
    p.add_argument("--verify-connection", action="store_true")
    p.add_argument("--send", action="store_true", help="REAL send. Default is dry-run.")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--skip-gate", action="store_true", help="dangerous: skip the pre-send re-check")
    a = p.parse_args(argv)

    if a.verify_connection:
        try:
            verify_connection()
            return 0
        except (ConnectGateError, TransportError) as e:
            log.error(str(e))
            return 2

    try:
        res = send_batch(a.outbox, dry_run=not a.send, limit=a.limit, skip_gate=a.skip_gate)
    except (ConnectGateError, TransportError) as e:
        log.error(str(e))
        return 2

    mode = "DRY RUN" if res["dry_run"] else "SENT"
    print(f"\n{mode}: {len(res['sent'])} · skipped: {len(res['skipped'])} · failed: {len(res['failed'])}")
    for name, why in res["skipped"]:
        print(f"  skip  {name}: {why}")
    for name, why in res["failed"]:
        print(f"  FAIL  {name}: {why}")
    if res["dry_run"] and res["sent"]:
        print("\nThis was a dry run — nothing was transmitted. Re-run with --send to actually send.")
    return 1 if res["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
