# Offer — Denial Recovery, for US independent practices

## Who it is for
An independent US practice (behavioural health, primary care, or a single-specialty group),
roughly 1–10 providers, billing insurance, that can export a claims/denial report from its
practice management system. **Not for:** hospital systems, practices with no denials, practices
whose billing is fully outsourced to a firm that already does denial work, and any practice on the
exclusion list in `shariah/c01.md` §8.

## The chain of three
### 0. Denial Recovery Audit — **free**
**What they give:** one de-identified claims export covering the last 12 months. Required columns:
date of service, CPT/HCPCS, payer, CARC/RARC denial code, billed amount, allowed amount, paid
amount, claim status, last action date. **Forbidden columns — refused by the ingest, not merely
discouraged:** patient name, DOB, address, MRN, member ID, SSN.

**What they get, within 2 business days:**
1. Total denied dollars in the period, and how much of it is **still appealable** by payer-specific
   timely-filing window — with the claims that have already expired shown separately, because that
   number is the honest one.
2. The top denial reasons by dollar, each with what it actually means and whether it is a coding
   fix, a documentation fix, or a payer error.
3. A ranked worklist of the highest-value recoverable claims.
4. A stated confidence and an explicit list of what the analysis could **not** determine from the
   file supplied.

**What it costs them:** nothing, and there is no obligation. **What it costs us:** minutes of
compute. This is the attraction offer and it is genuinely useful whether or not they ever buy.

### 1. Denial Recovery Sprint — **$1,500 flat, one time** *(core offer)*
14 calendar days. We prepare, for up to **40 claims** selected from the audit worklist by dollar
value and appealability:
- a completed appeal packet per claim — appeal letter citing the specific CARC/RARC, the payer's
  own published appeal route and deadline, and the documentation checklist the practice must attach;
- a corrected-resubmission worklist for claims that need a coding or modifier fix rather than an
  appeal;
- a one-page summary of the systemic causes, so the same denials stop recurring;
- a 30-minute handover call.

**The practice submits the appeals.** We prepare them. This boundary is deliberate: submitting on
their behalf would require system access, a BAA and identified patient data, all of which this
offer is designed to avoid.

### 2. Recovery Programme — **$4,000 flat, 30 days** *(premium option)*
Everything in the Sprint, for up to **150 claims**, plus weekly progress review against outcomes
the practice reports back, plus a denial-prevention rule set written against their top five recurring
denial reasons. Same flat-fee structure, same boundaries.

## Price and why
$1,500 is anchored to the practice's own number, not to our cost. The audit states the recoverable
total *before* the price is discussed; the Sprint is only offered when that total is materially
larger than the fee (see Guarantee 1). Retrieved industry data puts rework cost at $25–$181 per
claim (`research/evidence/c01.md`); at 40 claims the practice's own internal cost of doing this
work is $1,000–$7,240 in staff time they do not have.

**Flat fee, never a percentage of recoveries.** Reasoning in `shariah/c01.md` §3 and `DECISIONS.md`.

## Guarantees — both are inside our control, which is why they are survivable
1. **We will not sell you the Sprint unless the audit finds at least $7,500 (5×) in still-appealable
   denied claims.** If it does not, we say so and the engagement ends at the free audit. This is
   enforced in code (`system/score/`), not by good intentions.
2. **Delivery guarantee: every appeal packet delivered within 14 calendar days of receiving a
   complete data export, or the full $1,500 is refunded.** Our deadline, our control, our risk.

**What is deliberately NOT guaranteed: that any payer pays.** No recovery-amount promise, no
"typically recover X%" claim. Payer behaviour is outside our control and promising it would be
both untrue and *gharar*. Any competitor promise of a recovery percentage should be read with that
in mind.

## Refund conditions, stated unambiguously
- Guarantee 2 missed → **full refund**, no conditions, no partial credit.
- Practice supplies an incomplete or unreadable export and does not correct it within 7 days →
  engagement paused, not billed; if already paid, **full refund**.
- Practice changes its mind before we begin work → **full refund**.
- Practice changes its mind after packets are delivered → **no refund**; the work product exists
  and has been handed over.
- Payer denies an appeal → **no refund**. Stated plainly here and in the proposal, because a
  customer discovering this after paying would be a fair complaint.

## Terms
Flat fee, payable in full before work begins. No instalments, no credit, no financing, no interest
on late payment. Scope, claim count and deadline fixed in writing before payment. Data supplied is
used solely for the engagement, is not retained beyond 30 days after delivery, and is never resold,
aggregated or used for training. Either party may decline to proceed before work begins.

## Buying path
**understand** — a short outreach message naming one specific, verifiable observation about their
practice and what denials at their specialty and state typically cost →
**see proof** — the free audit, run on *their own data*, which is the proof; there are no case
studies because we have no results yet and will not borrow anyone else's →
**request** — they reply to the audit asking for the Sprint →
**pay** — one flat payment, before work starts *(payment rail is a §1.1 Connect/Spend gate — not
set up in this session)* →
**receive** — packets within 14 days, handover call, follow-up at 30 days to log the real outcome
into `metrics/ledger.csv`.
