"""
Audit-slot ledger.

Several templates say "I am doing four free denial audits in {{state}} this month" and
"Two of this month's four audit slots are gone". At automated volume those sentences are
false the moment the fifth email goes out — unless the cap is real.

So the cap is real. This module enforces it: four audit OFFERS per state per calendar
month. The engine refuses to render a fifth. That is what makes the copy true, and it is
why `audit_slots_four_per_state_month` is the one claim marked substantiated.

Consequence, stated plainly: this caps SEQUENCE_1, _3 and _6 step-1 sends at 12/month
across all three states. That is a deliberate throughput ceiling imposed by the copy. If
you want volume, the copy has to change — not the ledger.
"""
from __future__ import annotations
import json, pathlib, datetime as dt
from threading import Lock

SLOTS_PER_STATE_PER_MONTH = 4
LEDGER = pathlib.Path("data/audit_slots.json")
_lock = Lock()

# Steps whose copy asserts the four-slot scarcity.
SCARCITY_STEPS = {"SEQUENCE_1.1", "SEQUENCE_1.4", "SEQUENCE_3.1", "SEQUENCE_6.1"}


class SlotsExhausted(Exception):
    pass


def _period(when: dt.date | None = None) -> str:
    d = when or dt.date.today()
    return f"{d.year:04d}-{d.month:02d}"


def _read() -> dict:
    if not LEDGER.exists():
        return {}
    return json.loads(LEDGER.read_text())


def _write(data: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def used(state: str, when: dt.date | None = None) -> int:
    return len(_read().get(_period(when), {}).get(state, []))


def remaining(state: str, when: dt.date | None = None) -> int:
    return max(0, SLOTS_PER_STATE_PER_MONTH - used(state, when))


def claim(state: str, lead_id: str, when: dt.date | None = None) -> int:
    """Consume one slot. Raises SlotsExhausted rather than letting the copy become false."""
    with _lock:
        data = _read()
        period = _period(when)
        bucket = data.setdefault(period, {}).setdefault(state, [])
        if lead_id in bucket:
            return SLOTS_PER_STATE_PER_MONTH - len(bucket)
        if len(bucket) >= SLOTS_PER_STATE_PER_MONTH:
            raise SlotsExhausted(
                f"{state} has used all {SLOTS_PER_STATE_PER_MONTH} audit slots for {period}. "
                f"The copy says 'four free denial audits in {state} this month'. Sending a fifth "
                f"would make that sentence false, so it is refused. Wait for next month, raise "
                f"SLOTS_PER_STATE_PER_MONTH *and* amend the copy, or route this lead to a "
                f"sequence whose step 1 makes no scarcity claim (SEQUENCE_2, _4, _5)."
            )
        bucket.append(lead_id)
        _write(data)
        return SLOTS_PER_STATE_PER_MONTH - len(bucket)


def slots_gone(state: str, when: dt.date | None = None) -> int:
    """For SEQUENCE_1.4's 'Two of this month's four audit slots are gone.'"""
    return used(state, when)
