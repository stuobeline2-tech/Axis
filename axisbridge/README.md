# Axisbridge outbound pipeline

Independent mental health practices in TX / FL / GA. The pipeline's only success event is
**audit agreed** — a prospect asking for the BAA and sending denied claims. No calls booked,
no prices quoted, no closing.

```bash
pip install aiohttp dnspython requests

export AXISBRIDGE_POSTAL_ADDRESS="<real postal address>"   # CAN-SPAM, no default
export AXISBRIDGE_PRIVACY_URL="https://www.axisbridgemedical.com/privacy"
export AXISBRIDGE_BAA_PDF="/path/to/signed-baa.pdf"        # REPLY_A refuses without it

python -m axisbridge.lead_engine --validate-taxonomies     # do this FIRST
python -m axisbridge.lead_engine --states TX FL GA
python -m axisbridge.outreach_engine --check-claims        # exits 1 while anything is unsubstantiated
python -m axisbridge.outreach_engine --export-prospects data/prospects.csv
node system/outbound/presend.mjs --outbox outbox/          # checks 1-13
#   then a human reads the batch — check 14, the Send gate

# --- transport (Instantly) ---
export INSTANTLY_API_KEY="..."                              # Settings > API in Instantly, v2 key
export AXISBRIDGE_INSTANTLY_EACCOUNT="anthony@axisbridgemedical.com"
export AXISBRIDGE_INSTANTLY_EACCOUNT_SEQ6="anthony@<a different domain>"   # SEQUENCE_6 only

python -m axisbridge.transport_instantly --verify-connection    # one real, harmless GET — do this first
python -m axisbridge.transport_instantly --outbox outbox/       # DRY RUN by default, no network call
python -m axisbridge.transport_instantly --outbox outbox/ --send --limit 20   # the actual Send gate

python -m axisbridge.inbox_monitor --sla                   # escalations past 2 hours
```

## Transport (`transport_instantly.py`)

**Endpoint shapes are reconstructed from search snippets, not read from live docs** —
`developer.instantly.ai` was egress-blocked in the session that wrote this. Field names
believed correct: `eaccount`, `to_address`, `subject`, `body{html,text}`, `campaign_id`
(nullable), `reply_to_uuid`; Bearer auth. **Run `--verify-connection` before the first
batch** — one real, harmless `GET /accounts` call that surfaces a wrong field name
immediately instead of failing silently mid-batch. Confirm against Instantly's own docs
before volume.

This pipeline owns sequencing — day offsets, the claims gate, the four-slot scarcity
gate, thread linkage. Instantly is used purely as a send transport for an
already-rendered, already-gated message, never as its own campaign automation:
uploading leads into an Instantly campaign would let Instantly's step engine fire
follow-ups that never passed the claims gate.

Defaults to **dry run** — `--send` is required for a real transmission, and even then it
re-runs the JS pre-send gate immediately beforehand (the outbox may have changed since
it last ran) unless `--skip-gate` is explicitly passed. A reply-step artifact refuses to
send if no thread was recorded for that prospect+sequence — it will not silently start a
new thread. A failed API call is logged and left in `outbox/`, never moved to `sent/`,
never written to `metrics/ledger.csv` — only a confirmed 2xx produces a ledger row.
SEQUENCE_6 sends from its own configured mailbox, per the brief's "different sending
domain" instruction.

`tests/test_transport_instantly.py` (16 tests) never calls the real API — `requests`
is mocked at the transport boundary throughout, since no API key or real prospect
exists in this environment to test against.

## Four things that will stop you, on purpose

**1. Ten of twelve sequence steps are blocked.** `claims_register.json` holds every factual and
results claim the copy makes. A step cannot render while a claim it makes is unsubstantiated.
The templates were **not rewritten** — the brief said verbatim and that was honoured. The send
is gated instead. `--check-claims` lists what each claim needs. Currently blocked: SEQUENCE_1.1,
1.2, 1.4, 2.2, 2.4, 4.1, 4.2, 4.3, 5.2, 6.1, 6.2 and REPLY_B.

**2. Four audit slots per state per month, enforced.** The copy says "four free denial audits in
{{state}} this month". `scarcity.py` makes that literally true by refusing to render a fifth.
Ceiling: 12 scarcity-sequence step-1 sends per month across all three states. To go faster, the
copy has to change — not the ledger.

**3. The taxonomy set is 39 codes, not the compiled 71.** The compiled set lives on the VPS and
was not retrievable. What ships is a reconstruction from the NUCC standard across all six
categories, with per-code confidence, and it warns on every run. `--validate-taxonomies` queries
NPPES once per code and names every code returning zero, so a wrong code is visible immediately
rather than silently shrinking the funnel. **Replace `taxonomies.CODES` before the production pull.**

**4. There is no `send()`.** This builds and validates a queue. Attaching a transport is a
separate, named act. See the SENDING note in `outreach_engine.py`.

## Phase 3 is partial
`REPLY_A` and `REPLY_B` are implemented. **`REPLY_C` arrived truncated mid-sentence and `REPLY_D`
and `REPLY_E` were never sent.** They are not invented. A reply matching C is recognised and
escalated *by name* so it is not lost in a generic bucket; D/E-shaped replies (pricing,
not-interested) escalate too. No automated reply ever states a price.

**Opt-out is handled ahead of everything else.** Every email says "Reply STOP to opt out", so STOP
is matched first and suppression is written before any other processing. It never sits in the
escalation queue waiting on the 2-hour SLA — that is the one reply where a human SLA is not good
enough.

## Files
| | |
|---|---|
| `config.py` | states, payers, denial reasons, ICP exclusions, forbidden tokens |
| `taxonomies.py` | the six-category code set + shortfall warning |
| `claims_register.json` / `claims.py` | truthfulness gate |
| `scarcity.py` | audit-slot ledger |
| `templates.py` | the copy, verbatim |
| `routing.py` | one sequence per lead |
| `lead_engine.py` | NPPES → cluster → exclude → crawl → MX verify |
| `outreach_engine.py` | render → `outbox/` (no transport) |
| `inbox_monitor.py` | classify → reply / suppress / escalate |
