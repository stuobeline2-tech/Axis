# Metrics definitions

`ledger.csv` records **real events only**. There are no seeded, illustrative or example rows. It is
currently header-only, and that is the correct state: nothing has been contacted, because nothing
has been sent.

## Event rows
| column | meaning |
|---|---|
| `event_id` | monotonic integer |
| `ts` | ISO-8601 UTC, when the event actually happened |
| `prospect_id` | FK to `data/prospects.csv` |
| `stage` | one of: `contacted`, `replied`, `positive_reply`, `call_booked`, `proposal_sent`, `paid`, `refunded`, `churned` |
| `amount_gbp` | money actually moved. Blank unless stage is `paid` or `refunded` |
| `cost_gbp` | direct cost attributable to this event |
| `fulfilment_hours` | real clock hours, recorded after the fact, not estimated before |
| `note` | free text |

## Derived metrics — computed only from real rows
- **Revenue per 100 prospects** = Σ`amount_gbp` where stage=`paid` ÷ (count distinct contacted ÷ 100)
- **Profit per 100 prospects** = (Σ paid − Σ refunded − Σ cost) ÷ (contacted ÷ 100)
- **Revenue per human hour** = Σ paid ÷ Σ`fulfilment_hours` + operator hours logged
- **Stage conversion** = distinct prospects reaching stage N ÷ distinct reaching stage N−1
- **Refund rate** = count refunded ÷ count paid
- **Fulfilment time** = mean `fulfilment_hours` per paid engagement

Every one of these is **undefined on zero rows** and is reported as `null`, never as `0%` and never
as an estimate. A dashboard that shows a number where no event exists is a lie about the state of
the business.

## Assumptions live elsewhere
Forecasts belong in `DECISIONS.md` labelled `ASSUMPTION:` with a basis and a range. They never
enter `ledger.csv`. That separation is the whole point of the file.
