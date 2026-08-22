"""Phase 2 routing. Exactly one sequence per lead."""
from __future__ import annotations

PREMIUM_CREDENTIALS = {"MD", "PMHNP", "PsyD"}   # psychiatry / PMHNP / clinical psychology


def assign_sequence(lead: dict) -> tuple[str, str]:
    """-> (sequence_name, why). Order matters: earlier rules win."""
    if lead.get("has_open_billing_job_posting"):
        return "SEQUENCE_4", "open billing/front-desk job posting (48hr SLA trigger)"

    if lead.get("prior_sequence") and not lead.get("ever_replied") \
            and (lead.get("days_since_sequence_ended") or 0) >= 90:
        return "SEQUENCE_6", "completed a sequence 90+ days ago with zero replies"

    if lead.get("entity_type") == "org" and (lead.get("clinician_count") or 0) > 1:
        return "SEQUENCE_5", f"group practice, {lead['clinician_count']} clinicians"

    months = lead.get("enumeration_months")
    if months is None:
        return "SEQUENCE_1", "enumeration age unknown — defaulting to the highest-volume sequence"
    if months < 18:
        return "SEQUENCE_2", f"enumerated {months}mo ago (9-18mo band)"
    if months < 36:
        return "SEQUENCE_1", f"enumerated {months}mo ago (18-36mo band)"
    if lead.get("credential") in PREMIUM_CREDENTIALS:
        return "SEQUENCE_1", f"premium specialty ({lead['credential']}) overrides the 36+ band"
    return "SEQUENCE_3", f"enumerated {months}mo ago (36+ band)"


def enumeration_band(months: int | None) -> str:
    if months is None:
        return "unknown"
    if months < 18:
        return "9-18mo"
    if months < 36:
        return "18-36mo"
    return "36+"
