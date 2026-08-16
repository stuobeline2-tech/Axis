# Axis

Presell machine for a single offer: **recovering unsold estimates for home service contractors.**

Target: **$250/day** ($7,500/mo) through **8 retained clients at $1,000/mo**. Eight customers,
not a subscriber base — that constraint drives every decision here.

## The offer

Contractors send estimates and rarely follow up. Industry close rates sit around **23–30%**, most
estimates receive **one follow-up or none**, and **most deals that do close take four or more contacts**.
That backlog is revenue they already paid to generate. Axis reactivates it, under the contractor's brand,
on the contractor's own prior customers.

| | |
|---|---|
| Pilot | **$500 flat** — last 90 days of unsold estimates, 3 weeks, delivered by hand |
| Retainer | **$1,000/mo** — ongoing follow-up on new estimates |
| Qualified trade | average job **≥ $2,500**, **≥ 15 estimates/month**, uses a CRM |

**There is deliberately no product yet.** The pilot is delivered manually. Automation gets built after
two paid pilots show what delivery actually costs — building it now is how you build the wrong thing.

## Halal / shariah constraints, as enforced rules

These are implemented, not aspirational.

- **Flat, defined fees.** No percentage of revenue, no interest, nothing contingent on a client's
  financing products (contractor financing is interest-based — we neither build nor promote it).
  Scope, duration and deliverable are agreed in writing before payment. Avoids *riba* and *gharar*.
- **The calculator runs on the client's own numbers.** The single external assumption (recovery rate)
  is labelled, adjustable, conservative by default, and every limitation is printed on screen.
- **It tells you when not to sell.** Below a real payback threshold, `roi-calculator` says the service
  isn't worth buying, and `lead-engine` refuses to queue the lead. See `test/score.test.mjs`.
- **No deception in outreach.** The call script opens by naming itself as a cold call. No invented
  urgency, no borrowed case studies presented as your results, no fake personalisation.
- **Contact only where a relationship exists.** Reactivation goes to the *client's* prior estimate
  contacts, under the client's brand, with approval. Never a scraped or purchased list.
- **Honest reporting.** A job counts as recovered only when the client confirms it. A pilot that
  produces nothing is reported as producing nothing.

## Layout

```
roi-calculator/   index.html — the sales conversation. Open it live on every call.
lead-engine/      Google Places search + fit scoring → queued leads
pipeline/         CRM for ~100 conversations, and the real funnel rates
outreach/         call script, email sequence — the actual words
delivery/         pilot checklist, 5-touch sequence, attribution log
lib/db.mjs        SQLite (node:sqlite — no dependencies)
```

## Setup

Node ≥ 22.5. No install step; there are no dependencies.

```bash
git clone <this repo> && cd Axis
npm test                       # 9 tests on the qualification logic
open roi-calculator/index.html
```

For real lead data, set a [Google Places API (New)](https://console.cloud.google.com) key
(free monthly credit covers early volume — set a billing cap anyway):

```bash
export GOOGLE_PLACES_API_KEY=...
```

## Daily loop

```bash
# 1. build the list (once per metro/trade)
npm run leads -- --metro "Dallas TX" --trades roofing,hvac,remodeling
npm run leads -- --metro "Dallas TX" --trade roofing --dry-run   # preview scoring, no API key, no spend

# 2. today's call list — highest score, never contacted
npm run next

# 3. log every dial, including the no-answers
npm run pipeline -- touch 42 call --outcome spoke --note "owner Rick, ~45 est/mo, $9k ticket"
npm run pipeline -- move 42 demo

# 4. see the truth
npm run funnel
```

`npm run funnel` prints conversion at each stage plus current MRR and how many clients remain to
target. If 100 dials aren't producing ~2 demos, the script is wrong — fix it before dialling 100 more.

## Expected shape

| Weeks | Activity | Outcome |
|---|---|---|
| 1–2 | Build list, learn the calculator cold | machine ready |
| 3–6 | 40 dials/day → ~100 conversations | ~20 demos → **2 pilots** |
| 7–12 | Deliver pilots by hand, keep dialling | **~4 retained ≈ $4k/mo** |
| 4–6 mo | Convert, referrals, begin automating | **8 retained ≈ $8k/mo** |

Honest expectation: **months 5–7**, not weeks. The dominant failure mode is stopping outreach to write
code. The repo has no product in it precisely to make that harder.

## Cost to run

~$60–115/mo — secondary sending domain, three pre-warmed inboxes, a sending platform, list
verification. Everything in this repo is free to run. Never send cold email from your primary domain.

## Compliance

CAN-SPAM (US) and CASL (Canada) apply to the cold email; **CASL is stricter and generally requires
consent** — prefer phone for Canadian prospects. TCPA governs SMS: reactivation messages are sent by
the client, from the client's number, to the client's own prior customers. Details in
`outreach/email-sequence.md` and `delivery/reactivation-sequence.md`. This is operational guidance,
not legal advice — have the client agreement reviewed before signing the first one.
