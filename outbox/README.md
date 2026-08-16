# outbox/ — drafted, unsent artifacts

**Currently empty of artifacts, and that is the honest state, not an oversight.**

An artifact is only drafted from a real prospect row in `data/prospects.csv` carrying a
`source_url`, a `retrieved_at` and a specific `observation` about that business.
`data/prospects.csv` holds zero rows, because no prospect data could be retrieved in this session —
NPPES and every other data source is egress-blocked (`research/CAPABILITY-CONSTRAINT.md`).

Writing plausible-looking drafts to fill this directory would breach §2.1. So it stays empty.

The generator refuses in three ways rather than producing filler:
- no `contact_email` → no artifact
- `pecr_class` is anything other than `corporate_subscriber` → no artifact (PECR consent rule)
- no specific `observation` → **no artifact**, rather than a generic template

Once `data/prospects.csv` has real rows:
```bash
export SENDER_NAME=... SENDER_ENTITY=... SENDER_POSTAL_ADDRESS=... SENDER_PRIVACY_URL=...
node system/generate/outreach.mjs      # draft into outbox/
node system/outbound/presend.mjs       # checks 1-13; exits non-zero on any failure
# then a human reads the batch — that is check 14, and it is the Send gate
```
