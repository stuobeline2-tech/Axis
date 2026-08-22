"""Truthfulness gate. A sequence cannot send while a claim it makes is unsubstantiated."""
from __future__ import annotations
import json, pathlib

REGISTER_PATH = pathlib.Path(__file__).with_name("claims_register.json")


class UnsubstantiatedClaim(Exception):
    pass


def load() -> dict:
    return json.loads(REGISTER_PATH.read_text())["claims"]


def unsubstantiated(register: dict | None = None) -> dict[str, dict]:
    reg = register if register is not None else load()
    return {k: v for k, v in reg.items() if not v.get("substantiated")}


def blocked_steps(register: dict | None = None) -> dict[str, list[str]]:
    """-> {"SEQUENCE_1.1": ["most_practices_sitting_on_4_to_8k"], ...}"""
    out: dict[str, list[str]] = {}
    for key, claim in unsubstantiated(register).items():
        for step in claim.get("appears_in", []):
            out.setdefault(step, []).append(key)
    return out


def assert_sendable(step_id: str, register: dict | None = None) -> None:
    blocked = blocked_steps(register).get(step_id)
    if blocked:
        raise UnsubstantiatedClaim(
            f"{step_id} is blocked by {len(blocked)} unsubstantiated claim(s): "
            + ", ".join(blocked)
            + ". Substantiate them in axisbridge/claims_register.json, or amend the copy. "
              "The template was NOT rewritten."
        )


def report() -> str:
    reg = load()
    bad = unsubstantiated(reg)
    lines = [f"CLAIMS REGISTER — {len(reg) - len(bad)}/{len(reg)} substantiated", ""]
    if not bad:
        lines.append("All claims substantiated. Every sequence is clear to send.")
        return "\n".join(lines)
    by_step = blocked_steps(reg)
    lines.append(f"{len(bad)} unsubstantiated claim(s) blocking {len(by_step)} step(s):")
    lines.append("")
    for k, c in bad.items():
        lines.append(f"  [{c['type']}] {k}")
        lines.append(f"    says:     \"{c['text'][:100]}{'...' if len(c['text']) > 100 else ''}\"")
        lines.append(f"    appears:  {', '.join(c['appears_in'])}")
        lines.append(f"    needs:    {c['required']}")
        lines.append("")
    lines.append("BLOCKED STEPS: " + ", ".join(sorted(by_step)))
    return "\n".join(lines)
