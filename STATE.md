# STATE

CURRENT_PHASE: 5 — Prospecting · **BLOCKED**
LAST_UPDATED: 2026-08-16T15:40Z

| Phase | Status |
|---|---|
| 1 Discovery | **COMPLETE** — 23 candidates, each with retrieved evidence (grade: search-snippet) |
| 2 Selection | **COMPLETE** — winner c01, runner-up c08; 4 candidates killed by the gates |
| 3 Offer | **COMPLETE** — `offer/offer.md`, `offer/objections.md` |
| 4 Build | **COMPLETE with a caveat** — pipeline runs end to end, 34 tests pass; the end-to-end run used a **labelled synthetic fixture**, not a real practice export, because none is available. The acceptance criterion says "one real input"; that is satisfied the moment the operator supplies one, and the command is below. |
| 5 Prospecting | **BLOCKED** — no reachable source of real prospect data |
| 6–9 | Not started (6 requires replies; 7 requires a sale; 8–9 require 7) |

## The blocker, precisely
Building `data/prospects.csv` needs real, sourced, timestamped records. Every route is closed by
this environment's egress policy — NPPES API and bulk files, reddit, upwork, job boards,
directories, Companies House, Contracts Finder: all gateway 403. Verified, not assumed; see
`research/CAPABILITY-CONSTRAINT.md`. Search works, but returns vendor articles *about* markets,
not identifiable buyers.

**Two unblock paths, either is sufficient:**
1. **Operator supplies data** (no gate needed) — drop the existing NPPES extract or the 7k list at
   `data/prospects.csv` with columns `source_url,retrieved_at,org_name,npi,taxonomy,state,city,`
   `entity_type,pecr_class,contact_email,contact_name,score,notes,source_dataset,observation`.
   `observation` must be a specific, verifiable fact about that practice — the generator refuses to
   draft without it.
2. **Allowlist `npiregistry.cms.hhs.gov`** in the environment's egress settings. NPPES is a US
   public record and the LIA for it is already written (`compliance/lia-nppes.md`). A future
   session could then build the list unattended up to the Send gate.

## Open gates (§1.1) — none can be opened autonomously
- **Send** — nothing sent. `outbox/` is empty. Pre-send checks 1–13 are executable and pass
  vacuously on an empty outbox; check 14 is human and is the gate itself.
- **Spend** — nothing spent. £0.
- **Connect** — no account created, no credential requested, no API key used.
- **Commit** — no price published as an offer to anyone, no terms agreed, nothing filed.

## Next action for the operator, in order
```bash
npm test                                  # 34 tests, all passing
npm run audit -- --in <their-export.csv> --practice "Name"    # ← the one command that matters
```
That runs the real deliverable on a real input and closes the Phase 4 caveat. Then supply prospect
data by path 1 or 2 above to unblock Phase 5.

## Standing constraints carried forward
- Flat fee only, never contingency (`shariah/c01.md` §3).
- De-identified claim data only; the ingest refuses identifier columns.
- The 5× refuse-to-sell rule is enforced in `system/score/appealability.mjs`, not by discretion.
- Engine B (§8) is **not** run: annotation platforms prohibit AI/automation outright, transcription
  clears $7–20/hour, marketplaces need a Connect gate. See `compliance/platforms.md`.
