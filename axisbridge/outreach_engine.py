"""
PHASE 2 — render sequenced outreach into outbox/ as unsent artifacts.

    python -m axisbridge.outreach_engine --check-claims
    python -m axisbridge.outreach_engine --leads data/leads_database.json --due-today

This module RENDERS and QUEUES. It does not transmit. Transmission is a separate,
deliberate act — see SENDING, below.
"""
from __future__ import annotations
import argparse, json, logging, os, pathlib, re, sys
from datetime import date, datetime, timedelta

from . import config, claims, scarcity, templates

log = logging.getLogger("outreach_engine")
VAR_RE = re.compile(r"\{\{(\w+)\}\}")

# (?<![a-z0-9.-]) anchors each host to a genuine boundary so a booking domain cannot be
# matched as a substring of an unrelated domain.
BOOKING_RE = re.compile(
    r"(?<![a-z0-9.\-])(calendly\.com|cal\.com|savvycal\.com|tidycal\.com|"
    r"youcanbook\.me|acuityscheduling\.com|hubspot\.com/meetings|meetings\.hubspot\.com|"
    r"chilipiper\.com|zcal\.co)"
    r"|\bbook a (call|time|slot|meeting)\b|\bschedule a (call|demo|meeting|chat)\b"
    r"|\bgrab a (time|slot)\b|\bpick a time\b")


class RenderRefused(Exception):
    pass


def footer() -> str:
    addr = os.environ.get(config.FOOTER_ADDRESS_ENV, "").strip()
    if not addr:
        raise RenderRefused(
            f"{config.FOOTER_ADDRESS_ENV} is not set. CAN-SPAM requires a genuine physical "
            f"postal address in every commercial email. There is no placeholder default — a "
            f"fake address in a compliance footer is worse than no footer, because it looks "
            f"compliant. Set it and re-run."
        )
    privacy = os.environ.get(config.FOOTER_PRIVACY_ENV, "").strip()
    privacy_line = f"\nPrivacy notice: {privacy}" if privacy else ""
    return f"\n\n{addr}{privacy_line}\n{config.FOOTER_OPTOUT}"


def variables_for(lead: dict) -> dict[str, str]:
    return {
        "first_name": (lead.get("first_name") or "").strip() or "there",
        "practice_name": lead.get("practice_name") or "",
        "city": lead.get("city") or "",
        "state": lead.get("state") or "",
        "credential": lead.get("credential") or "",
        "payer": lead.get("payer") or "",
        "denial_reason": lead.get("denial_reason") or "",
        "clinician_count": str(lead.get("clinician_count") or ""),
    }


def substitute(text: str, variables: dict[str, str]) -> str:
    missing = []

    def repl(m):
        key = m.group(1)
        val = variables.get(key, "")
        if not val:
            missing.append(key)
        return val

    out = VAR_RE.sub(repl, text)
    if missing:
        raise RenderRefused(
            f"variable(s) {sorted(set(missing))} resolved empty. The brief says never invent a "
            f"value; only {{first_name}} has a fallback. Fix the lead record or drop the lead."
        )
    return out


def _guard(rendered: str, step_id: str) -> None:
    low = rendered.lower()
    for name in config.FORBIDDEN_IN_OUTREACH:
        if name.lower() in low:
            raise RenderRefused(f"{step_id}: '{name}' must not appear in outreach.")
    for tok in config.FORBIDDEN_PRICE_TOKENS:
        if tok.lower() in low:
            raise RenderRefused(f"{step_id}: price/offer token '{tok}' must never appear in outreach.")
    for banned in config.BANNED_OFFERS:
        if banned.lower() in low:
            raise RenderRefused(f"{step_id}: '{banned}' was removed deliberately and must not reappear.")
    # Host-boundary anchored. An earlier version matched the bare substring "cal.com", which
    # is inside "axisbridgemedical.com" — the company's own privacy URL silently refused every
    # email in the queue. Booking hosts must start at a real host boundary.
    if BOOKING_RE.search(low):
        raise RenderRefused(f"{step_id}: a scheduling link or booking CTA appeared. The only CTA is a reply.")


def render(lead: dict, sequence: str, step: templates.Step, *, register=None) -> dict:
    step_id = f"{sequence}.{step.step}"
    claims.assert_sendable(step_id, register)          # truthfulness gate

    if step_id in scarcity.SCARCITY_STEPS and step.step == 1:
        scarcity.claim(lead["state_code"], lead["lead_id"])   # raises SlotsExhausted

    variables = variables_for(lead)
    body = substitute(step.body, variables) + footer()
    _guard(body, step_id)
    subject = substitute(step.subject, variables) if step.subject else None
    if subject:
        _guard(subject, step_id)

    return {
        "to": lead["contact_email"],
        "prospect_id": lead["lead_id"],
        "org_name": lead["practice_name"],
        "sequence": sequence, "step": step.step, "step_id": step_id,
        "subject": subject,                                  # None => reply in existing thread
        "reply_in_thread": step.reply_in_thread,
        "body": body,
        "drafted_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "status": "AWAITING_SEND_GATE",
    }


def due_steps(lead: dict, today: date) -> list[templates.Step]:
    started = lead.get("sequence_started_on")
    if not started:
        return [templates.SEQUENCES[lead["sequence"]][0]]
    start = datetime.strptime(started, "%Y-%m-%d").date()
    sent = set(lead.get("steps_sent") or [])
    return [s for s in templates.SEQUENCES[lead["sequence"]]
            if s.step not in sent and start + timedelta(days=s.day) <= today]


def build(leads: list[dict], outbox: pathlib.Path, today: date) -> dict:
    outbox.mkdir(parents=True, exist_ok=True)
    written, refused = 0, []
    for lead in leads:
        if not lead.get("email_verified"):
            refused.append((lead.get("lead_id"), "email not verified")); continue
        if lead.get("opted_out"):
            refused.append((lead.get("lead_id"), "opted out")); continue
        seq = lead.get("sequence")
        if seq not in templates.SEQUENCES:
            refused.append((lead.get("lead_id"), f"no/unknown sequence {seq!r}")); continue
        for step in due_steps(lead, today):
            try:
                art = render(lead, seq, step)
            except (RenderRefused, claims.UnsubstantiatedClaim, scarcity.SlotsExhausted) as e:
                refused.append((lead.get("lead_id"), f"{seq}.{step.step}: {e}"))
                continue
            (outbox / f"{lead['lead_id']}-{seq}-{step.step}.json").write_text(json.dumps(art, indent=2) + "\n")
            written += 1
    return {"written": written, "refused": refused}


# ------------------------------------------------------------------------- SENDING
# There is no send() in this module, and that is deliberate.
#
# The repository's standing operating spec (§1.1) makes transmission to a real third
# party a stop-and-ask gate. This brief asks for unsupervised automated sending, which
# is the operator's call to make — but it is theirs to make explicitly, not something to
# be quietly inherited by importing an SMTP client into a queue builder.
#
# The queue this writes is validated by the existing gate:
#     node system/outbound/presend.mjs --outbox outbox/
# which enforces suppression, unsubscribe, postal address, PECR class and sourcing.
# Wire an ESP/SMTP transport to the validated queue as a separate, named component.

PROSPECT_COLUMNS = ["source_url","retrieved_at","org_name","npi","taxonomy","state","city",
                    "entity_type","pecr_class","contact_email","contact_name","score","notes",
                    "source_dataset","observation"]


def export_prospects(leads: list[dict], path: pathlib.Path) -> int:
    """Emit data/prospects.csv so the existing gate (system/outbound/presend.mjs) can validate."""
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PROSPECT_COLUMNS)
        w.writeheader()
        for l in leads:
            if not l.get("email_verified"):
                continue
            w.writerow({
                "source_url": l["source_url"], "retrieved_at": l["retrieved_at"],
                "org_name": l["practice_name"], "npi": (l.get("npis") or [""])[0],
                "taxonomy": l.get("taxonomy_code"), "state": l.get("state_code"),
                "city": l.get("city"), "entity_type": l.get("entity_type"),
                "pecr_class": l.get("pecr_class"), "contact_email": l.get("contact_email"),
                "contact_name": l.get("first_name"), "score": "",
                "notes": f"{l.get('sequence')}: {l.get('sequence_reason')}",
                "source_dataset": l.get("source_dataset"),
                "observation": l.get("observation") or "",
            })
    return sum(1 for l in leads if l.get("email_verified"))


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--leads", type=pathlib.Path, default=pathlib.Path("data/leads_database.json"))
    p.add_argument("--outbox", type=pathlib.Path, default=pathlib.Path("outbox"))
    p.add_argument("--check-claims", action="store_true")
    p.add_argument("--due-today", action="store_true")
    p.add_argument("--export-prospects", type=pathlib.Path,
                   help="write data/prospects.csv for the JS pre-send gate")
    a = p.parse_args(argv)

    if a.check_claims:
        print(claims.report())
        return 0 if not claims.unsubstantiated() else 1
    if not a.leads.exists():
        log.error("%s does not exist. Run lead_engine first.", a.leads)
        return 2
    leads = json.loads(a.leads.read_text())
    if a.export_prospects:
        n = export_prospects(leads, a.export_prospects)
        print(f"{n} prospect row(s) -> {a.export_prospects}")
    res = build(leads, a.outbox, date.today())
    print(f"{res['written']} artifact(s) queued to {a.outbox}")
    for lid, why in res["refused"][:40]:
        print(f"  refused {lid}: {why}")
    if len(res["refused"]) > 40:
        print(f"  ...and {len(res['refused']) - 40} more refusals")
    print("\nNext: node system/outbound/presend.mjs --outbox outbox/   (checks 1-13)")
    print("Then a human reads the batch. That is check 14, and it is the Send gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
