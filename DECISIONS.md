# DECISIONS (append-only)

## 2026-08-16T14:53:01Z — Treat the pre-existing repo contents as a Phase-1 candidate, not as completed work
The repository already contained a working presell machine targeting US home-service
contractors (unsold-estimate recovery, $500 pilot / $1,000-mo retainer), built on a prior
run without this spec. It has tests and a real ROI calculator, but no `STATE.md`, no
evidence files, no scored comparison against alternatives, no Shariah file and no real
prospect rows. Under §2.1 I cannot inherit its implied progress. Under §7 it is exactly
the kind of already-built asset that should be preferred over new construction *if it
scores highest* — so it enters Phase 1 as a candidate with its own evidence requirement
like every other. Nothing in it is deleted.

## 2026-08-16T15:02Z — Weights left at the spec default, deliberately
§6 permits one revision of the weights. I am not taking it. The default weights have a real flaw —
`competition_inv` and `acquisition_cost_inv` are scored but carry zero weight, so a saturated,
expensive-to-enter market is not penalised by the formula. I noticed that flaw *after* scoring,
which is exactly when re-weighting stops being modelling and starts being result-shopping. The
columns are recorded in `scoring.csv` so the operator can re-weight, and the qualitative penalty is
applied where it bites (c16 local SEO and c18 automation agency both score competition 2/10 and are
discussed as saturated in their evidence files) — but the published number stays on the spec's
weights.

## 2026-08-16T15:04Z — Winner: c01, Denial Recovery Sprint for US independent practices
**Score 6.80, highest of 23. Shariah 8/10, passes the gate with conditions recorded.**

**The case for it.** It wins on the three heaviest weights at once. *Ability to pay* 9/10: the buyer
is a business with revenue, and the thing being sold is money that is already theirs. *Urgency* 7/10
is real rather than manufactured — retrieved evidence puts initial denial rates at ~11.8% with
roughly 60% of denials never reworked, and timely-filing deadlines make some of that money expire
permanently, which is the rarest and most honest form of urgency: the asset actually disappears.
*Automation* 8/10 because the audit is a deterministic transformation of a file the client already
has. Add the §7 test — it is the only candidate where the operator already owns the offer, the
price, the sending infrastructure and the prospect data, so almost nothing has to be built to sell
it. §7 sets it as the benchmark any new candidate must beat on expected value; nothing beat it.

**The case against the runner-up, c08 (UK public sector WCAG 2.2 audit, score 6.40).** This is the
better *business* on almost every axis I care about personally: Shariah certainty 9/10 and the
cleanest screen in the set, a statutory duty with an expired grace period and a named enforcement
body, buyers who are publicly enumerable, findings that are reproducible by the client so truth is
guaranteed by construction, and a harm surface that is positive — disabled users of public
services. It loses on exactly one thing, and it is the thing weighted 0.20: **it cannot close
quickly.** A public body buys through procurement — framework, quote thresholds, purchase order,
finance approval. Its same-day close probability is 1/10, and against an objective function that
weights same-day cash highest, a 0.20 weight at 1/10 is a 1.2-point hole that its superiority
elsewhere does not fill. It is the right second candidate and the right thing to run when the
objective is 90-day rather than same-day. I am recording it as such rather than discarding it.

**What the Shariah gate actually did.** It was not decorative. c13 (UK invoice chasing) scored 6.20
— third overall, above five eligible candidates — and was killed because the commercial mechanic of
the trade is a demand for statutory interest at base + 8%, which is facilitation of riba, and
because the adjacent product is invoice finance. c23 (selling lead lists) and c11 (unread
AI-generated content sold as a client's own expertise) and c14 (bid writing) were also excluded.
Four candidates removed by the gate, one of them a top-three scorer.

## 2026-08-16T15:06Z — De-identified data only, and flat fee only
Two design decisions taken alone, both narrowing the business:
1. **The audit ingests de-identified claim-level data only** — no patient name, DOB, address, MRN
   or member ID. The ingest refuses identifier columns rather than trusting the sender. This makes
   the free tier deliverable without a BAA in the ordinary case and collapses the third-party harm
   surface, which `shariah/c01.md` identifies as the real one. It costs some analytic richness.
2. **Flat fee, never contingency.** The industry norm is a percentage of recoveries. That would be
   more lucrative and is how competitors price. It is rejected because the fee would be unknown at
   contract (gharar), because it converts our earnings into a share of an insurance settlement, and
   because it introduces a chance element. This is a real revenue sacrifice taken on purpose.

## 2026-08-16T15:35Z — Cash model for c01 (§6), with every probability labelled
No stage of this funnel has been run, so **every probability below is an ASSUMPTION**, not data.
None of it enters `metrics/ledger.csv`. The purpose of writing it down now is so that the first
real numbers can be compared against a hypothesis recorded *before* the test, per §9.

`Expected same-day revenue = N_contactable × P(reply) × P(reply→call) × P(call→close) × price`

- `ASSUMPTION: P(reply)` cold B2B email to US healthcare — **low 1.0% / base 2.0% / high 5.0%**.
  Basis: no first-party data. Range set from the general cold-email band; deliberately wide.
- `ASSUMPTION: P(reply→call)` — **low 15% / base 30% / high 45%**. Basis: the reply is to an offer
  of a free audit, so a meaningful share of replies are the audit request itself.
- `ASSUMPTION: P(call→close)` at $1,500, same day — **low 5% / base 15% / high 30%**.
- `price` = $1,500 (fixed, real — it is the operator's existing offer).
- `N_contactable` — **0 in this session.** No prospect data is reachable.

**With N = 0, expected same-day revenue is $0.** That is the actual answer for today and no other
number should be quoted. The model below is what it becomes at N = 500/day once the operator
supplies their existing list:

| Case | replies | calls | closes | same-day revenue |
|---|---:|---:|---:|---:|
| Low | 5 | 0.75 | 0.04 | **$56** |
| Base | 10 | 3.0 | 0.45 | **$675** |
| High | 25 | 11.25 | 3.38 | **$5,063** |

`Expected same-day profit = revenue − acquisition − fulfilment − software`
Software ≈ £100/mo sending stack amortised ≈ **£3/day**; acquisition ≈ £0 marginal (list already
owned); fulfilment ≈ 4–6 human hours per Sprint sold, incurred only on a sale.

- **Low case: $56 revenue − ~£3 software = roughly break-even to slightly negative** once any
  fulfilment hour is counted. **Stated plainly as required: the low case is negative.**
- Base case: ~$675 revenue, ~$670 gross of fulfilment; at 0.45 closes × 5 hours ≈ 2.25 human hours
  plus ~1 hour of send approval → `ASSUMPTION: expected net ≈ $200/human hour in the base case`.

**The honest caveat that matters more than the table.** A same-day close on a $1,500 B2B healthcare
service from a cold email sent that morning is improbable. The realistic first cash is day 3–14:
audit request → audit delivered in 2 business days → decision. Weighting same-day cash at 0.20 is
the spec's instruction and I have followed it in the scoring, but the operator should read the
30-day figure as the real one and treat the same-day column as a tie-breaker.

## 2026-08-16T15:38Z — Phase 5 declared BLOCKED rather than filled with plausible data
The pipeline is built and tested; what is missing is prospects. Every route to real prospect data
is closed in this session: NPPES API and bulk files, every job board, every directory, every review
site and every forum return a gateway 403 (evidence in `research/CAPABILITY-CONSTRAINT.md`). The
operator's own 184k NPPES records and 7k list live on their VPS, not in this repository.

I could have produced a `data/prospects.csv` of real-*looking* US practices from general knowledge.
That is precisely the failure §2.1 is written to prevent, and it would have been undetectable in a
skim. `data/prospects.csv` is therefore header-only, `outbox/` holds no artifacts, and Phase 5 is
`BLOCKED`. A blocked phase is a valid outcome; a fabricated one is a failed run.
I did not set an N target for Phase 5, because choosing a number I cannot meet would be theatre.
