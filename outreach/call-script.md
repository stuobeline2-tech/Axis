# Cold call script — primary channel

Cold call is the main channel for this vertical. Contractors answer their own phones,
decide without a committee, and respond to arithmetic. Email is the follow-up, not the opener.

**Volume target: 40 dials/day.** Expect ~8–12 conversations, ~2–3 real interest, ~1 booked demo.
If you are far off those after 100 dials, the script is wrong — not the market. Change one thing at a time.

---

## The rules that don't bend

- **Say who you are on the first breath.** No "I'm just following up" when there's nothing to follow up on.
  No pretending to be a past customer, a supplier, or an inbound lead.
- **No invented urgency.** No "I only have two spots", no fake deadline, no fake local case study.
- **No borrowed numbers.** Never quote another company's results as if they were yours. Until you have
  your own attribution log, you have *industry figures* and *their* numbers — nothing else.
- **If they're not a fit, tell them.** Low ticket or low volume means the fee won't pay back. Say so and
  end the call. This costs you nothing and is the whole reason a referral ever comes back.
- **Honour the first clear "no".** Remove them from the list. Don't dress a no up as an objection to handle.

---

## Opener (aim: earn 30 more seconds)

> "Hi — is this the owner? … My name's **[NAME]**, I'm calling from **[COMPANY]** here in **[CITY]**.
> I'll be straight with you, this is a cold call — can I have twenty seconds to tell you why I rang,
> and you can tell me to get lost?"

Naming the cold call disarms the reflex to hang up. Most owners say "go on."

**If gatekeeper:** "No problem — is [owner] around later? I'll try back. What's usually a good time?"
Don't pitch the gatekeeper. Log `--outcome gatekeeper` and call back at the stated time.

---

## The hook (one sentence, then stop talking)

> "You send out estimates every week that never get a yes and never get a no — they just go quiet.
> I follow those up for you, properly, for a few weeks after you've quoted. That's the whole thing."

Then **be silent.** The silence does the work. Let them respond first.

---

## Qualify — before you pitch anything

Ask these three. You need them for the calculator, and they tell you whether to keep going at all.

1. "Roughly how many estimates do you send out in a month?"
2. "Of those, about how many turn into actual jobs?"
3. "And what's a typical job worth to you?"

**Disqualify on the spot if:**

| Signal | What it means |
|---|---|
| Average job under ~$2,500 | Recovery can't cover a $1,000 fee. Not a fit. |
| Fewer than ~15 estimates/month | Too little volume for follow-up to find anything. |
| "We close nearly all of them" | No unsold backlog to work. Believe them and move on. |
| No system — quotes are verbal only | Nothing to export. Revisit if they adopt a CRM. |

Script for a genuine no-fit:

> "Honestly? On those numbers this wouldn't pay for itself, so I'm not going to pitch you.
> If your average job size climbs, call me. Appreciate your time."

That call was not wasted. That's the one that refers you.

---

## The arithmetic (only if they qualify)

Do it out loud, using **their** numbers, in their units:

> "So — 40 out, about 10 land. That leaves 30 a month that just… evaporate.
> At [their ticket] a job, if following those up properly recovered even *one* of them,
> that's [ticket] in work you already paid to quote for. That's the conversation I want to have."

Then the ask:

> "Can I put fifteen minutes in the diary and show you the numbers on your own business?
> If it doesn't stack up you'll see that in about two minutes and we'll both save the time."

---

## Objection handling

**"We already follow up."**
> "Most do once. The money's in the fourth and fifth touch — that's where the majority of these close,
> and it's the part that gets dropped when you're busy on the tools. How many times do yours actually go out?"

**"I don't have time for this."**
> "That's exactly why I called. The work is on my side — I need one export from your system and about
> twenty minutes of you once a week. That's it."

**"How much?"**
> "One-off pilot is $500 flat and I work your last 90 days of unsold quotes. If it produces, it's
> $1,000 a month after that. Flat fee, no percentage, cancel whenever. I'd rather you saw it work first."

**"Send me some information."**
> Usually a soft no. Test it: "Happy to — what specifically do you want to see, so I don't send you junk?"
> A real answer means send it. A vague one means: "Tell you what, I'll send a one-pager and try you
> next week." Then log it and actually try back.

**"Is this AI robocalling my customers?"**
> "No. It goes out under your name and your brand, to people who already asked you for a quote.
> You approve the messages before anything sends. I'm not cold-contacting strangers for you —
> that's a good way to get you in trouble, not a good way to get you jobs."

---

## Voicemail (leave one, once, then move on)

> "Hi [name], it's [NAME] at [COMPANY], [phone]. I work with [trade] companies around [city] on
> chasing up estimates that went quiet — the ones that never got a yes or a no. If that's a familiar
> problem, give me a ring on [phone]. If not, no need to call back. Thanks."

Under 20 seconds. Number twice. No hook, no pressure.

---

## Log every call

```
npm run pipeline -- touch <id> call --outcome no_answer|gatekeeper|spoke|booked|not_interested --note "..."
```

Log the no-answers too. The denominator is the only way to know whether the script or the list is the problem.
