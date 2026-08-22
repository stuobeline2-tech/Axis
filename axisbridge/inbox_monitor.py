"""
PHASE 3 — reply classification.

Classifies an inbound reply into exactly one action. Sends the matching template
VERBATIM, in-thread. Anything that does not clearly match is escalated to Anthony and
the lead's sequence is halted — it is never answered by a generated message.

Two things the brief did not specify that are implemented anyway:

1. OPT-OUT handling. Every email says "Reply STOP to opt out." A STOP reply must be
   honoured immediately and permanently. It cannot sit in an escalation queue waiting
   for a human — that is the one reply type where a two-hour SLA is not good enough and
   is arguably unlawful. STOP is matched first, before anything else, and suppression
   is written before any other processing.

2. BAA existence check. REPLY_A says "Signed BAA attached". An automated system cannot
   assert that a legal document is attached unless the document is actually configured
   and present. If it is not, REPLY_A is refused and escalated.
"""
from __future__ import annotations
import argparse, csv, json, logging, os, pathlib, re, sys
from datetime import datetime, timedelta, timezone

from . import claims, templates

log = logging.getLogger("inbox_monitor")

SUPPRESSION = pathlib.Path("compliance/suppression.csv")
ESCALATIONS = pathlib.Path("data/escalations.jsonl")
STATUS_LOG = pathlib.Path("data/reply_log.jsonl")
BAA_PATH_ENV = "AXISBRIDGE_BAA_PDF"
SLA = timedelta(hours=2)

# Matched in order. First match wins.
STOP_RE = re.compile(r"^\s*(stop|unsubscribe|remove me|opt[\s-]?out|take me off)\b", re.I | re.M)
STOP_ANYWHERE_RE = re.compile(r"\b(unsubscribe me|remove me from|stop emailing|do not (email|contact) me|opt me out)\b", re.I)

REPLY_A_RE = re.compile(
    r"\b(send (me )?(the |over the )?baa|yes[,.! ]*(please|send|go ahead|interested)?|"
    r"i'?m interested|we'?re interested|sounds good|let'?s do it|sign me up|"
    r"go ahead|send it (over|through)|happy to (try|take a look)|"
    r"where do i send|how do i (send|export)|what do you need from (me|us))\b", re.I)

REPLY_B_RE = re.compile(
    r"\b(hipaa|phi|offshore|overseas|outside the (us|country)|philippines|"
    r"business associate|baa (requirement|compliance)|data (security|protection|privacy)|"
    r"where (are|is) (your|the) (biller|staff|team) (based|located))\b", re.I)

# Kept so the classifier can RECOGNISE these and escalate them by name rather than
# dumping them into a generic "unmatched" bucket. No template exists to answer them.
REPLY_C_RE = re.compile(r"\b(already have (a |an )?(biller|billing|billing company|rcm)|we use [A-Z]|our billing (company|service)|we'?re covered|have someone)\b", re.I)
REPLY_D_E_HINT_RE = re.compile(r"\b(how much|what.{0,12}(cost|price|charge)|pricing|rates?|not interested|no thanks|remove)\b", re.I)


class ReplyRefused(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _append_jsonl(path: pathlib.Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(obj) + "\n")


def suppress(email: str, reason: str, source: str) -> None:
    """Written before anything else. Idempotent."""
    SUPPRESSION.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if SUPPRESSION.exists():
        with SUPPRESSION.open() as f:
            existing = {r["identifier"].strip().lower() for r in csv.DictReader(f) if r.get("identifier")}
    if email.lower() in existing:
        return
    new = not SUPPRESSION.exists() or SUPPRESSION.stat().st_size == 0
    with SUPPRESSION.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["identifier", "identifier_type", "added_at", "reason", "source"])
        w.writerow([email.lower(), "email", _now().isoformat(timespec="seconds"), reason, source])


def escalate(lead_id: str, email: str, body: str, why: str) -> dict:
    rec = {"ts": _now().isoformat(timespec="seconds"), "lead_id": lead_id, "from": email,
           "why": why, "excerpt": body.strip()[:400], "action": "HALT_SEQUENCE",
           "assigned_to": "Anthony", "status": "OPEN"}
    _append_jsonl(ESCALATIONS, rec)
    return {"action": "ESCALATE", "template": None, "halt_sequence": True, "reason": why, "record": rec}


def classify(body: str) -> str:
    """-> one of STOP | REPLY_A | REPLY_B | REPLY_C | UNMATCHED"""
    if STOP_RE.search(body) or STOP_ANYWHERE_RE.search(body):
        return "STOP"
    # HIPAA/offshore is checked before the yes-pattern: "yes but where are your billers
    # based?" is a compliance question, not a green light.
    if REPLY_B_RE.search(body):
        return "REPLY_B"
    if REPLY_A_RE.search(body):
        return "REPLY_A"
    if REPLY_C_RE.search(body):
        return "REPLY_C"
    return "UNMATCHED"


def handle(reply: dict, *, register=None) -> dict:
    """reply = {lead_id, from, body, received_at}"""
    email, body, lead_id = reply["from"], reply.get("body", ""), reply.get("lead_id", "")
    kind = classify(body)

    if kind == "STOP":
        suppress(email, "replied STOP / opt-out request", "inbox_monitor")
        out = {"action": "SUPPRESS", "template": None, "halt_sequence": True,
               "reason": "opt-out honoured immediately and permanently", "notify": []}
        _append_jsonl(STATUS_LOG, {"ts": _now().isoformat(timespec="seconds"), "lead_id": lead_id,
                                   "kind": kind, "action": out["action"]})
        return out

    if kind == "REPLY_A":
        baa = os.environ.get(BAA_PATH_ENV, "")
        if not baa or not pathlib.Path(baa).is_file():
            return escalate(lead_id, email, body,
                            f"REPLY_A says 'Signed BAA attached' but {BAA_PATH_ENV} is unset or the "
                            f"file does not exist. Refusing to send an email claiming an attachment "
                            f"that is not there.")
        try:
            claims.assert_sendable("REPLY_A", register)
        except claims.UnsubstantiatedClaim as e:
            return escalate(lead_id, email, body, str(e))
        out = {"action": "SEND", "template": "REPLY_A", "body": templates.REPLY_A,
               "attach": baa, "status": "AUDIT_AGREED", "halt_sequence": True,
               "notify": ["Abdikarim"], "reason": "audit agreed — the pipeline's terminal event"}
        _append_jsonl(STATUS_LOG, {"ts": _now().isoformat(timespec="seconds"), "lead_id": lead_id,
                                   "kind": kind, "action": "SEND", "status": "AUDIT_AGREED"})
        return out

    if kind == "REPLY_B":
        try:
            claims.assert_sendable("REPLY_B", register)
        except claims.UnsubstantiatedClaim as e:
            return escalate(lead_id, email, body,
                            f"REPLY_B blocked: {e} This reply makes a legal assurance about offshore "
                            f"business associates to a covered entity. It needs a source before it auto-sends.")
        return {"action": "SEND", "template": "REPLY_B", "body": templates.REPLY_B,
                "halt_sequence": False, "notify": [], "reason": "HIPAA/offshore question"}

    if kind == "REPLY_C":
        return escalate(lead_id, email, body,
                        "matches REPLY_C ('we already have a billing company') but REPLY_C was "
                        "truncated mid-sentence in the brief and REPLY_D/REPLY_E were never "
                        "supplied. No template exists to send. Not invented.")

    return escalate(lead_id, email, body, "does not clearly match any supplied template")


def sla_breaches(log_path: pathlib.Path = ESCALATIONS) -> list[dict]:
    if not log_path.exists():
        return []
    out = []
    for line in log_path.read_text().splitlines():
        rec = json.loads(line)
        if rec.get("status") != "OPEN":
            continue
        if _now() - datetime.fromisoformat(rec["ts"]) > SLA:
            out.append(rec)
    return out


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--classify", help="classify a reply body from the command line")
    p.add_argument("--sla", action="store_true", help="list escalations past the 2-hour SLA")
    a = p.parse_args(argv)
    if a.sla:
        b = sla_breaches()
        print(f"{len(b)} escalation(s) past the {SLA} SLA")
        for r in b:
            print(f"  {r['ts']}  {r['from']}  {r['why'][:80]}")
        return 1 if b else 0
    if a.classify:
        print(classify(a.classify))
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
