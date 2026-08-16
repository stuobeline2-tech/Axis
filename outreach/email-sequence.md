# Email sequence — support channel

Email supports the phone; it rarely closes on its own in this vertical. Use it to warm a list before
dialling, and to follow up after a call that didn't land.

## Legal floor (US CAN-SPAM / Canada CASL)

Not optional, and not merely legal housekeeping — misrepresenting who you are is deception.

- Real sender name and a real reply-to that you monitor.
- **Physical mailing address in every email.** CAN-SPAM requires it; CASL requires it too.
- Working one-click unsubscribe, honoured within 10 business days (do it same-day).
- Accurate subject lines — the subject must describe the actual content.
- **CASL is stricter than CAN-SPAM**: Canadian recipients generally need consent, with a narrow
  business-to-business exemption. If you're unsure about a Canadian prospect, call instead of emailing.

## Infrastructure

Never send from your primary domain. Buy a lookalike (`getaxis.co` alongside `axis.com`), warm it,
and send from there — if deliverability is damaged, your real domain survives.

| Item | Cost |
|---|---|
| Secondary domain | ~$12/yr |
| 3 pre-warmed inboxes | ~$15/mo |
| Sending platform | ~$37/mo |
| List verification | ~$5–15/mo |
| **Total** | **~$60–115/mo** |

Cap at ~30 sends/inbox/day. Volume beyond that buys spam folders, not replies.

---

## Touch 1 — day 0

**Subject:** estimates that went quiet

> Hi [First],
>
> Quick one — when [Company] sends out an estimate and the customer just goes quiet,
> what happens next?
>
> For most [trade] companies the honest answer is "one follow-up, then nothing." Which means a
> stack of quotes you already paid to produce is sitting there doing nothing.
>
> That's the only thing I do: structured follow-up on unsold estimates, under your brand,
> for a few weeks after you quote.
>
> Worth a ten-minute call?
>
> [NAME]
> [COMPANY] · [phone]
> [physical address]
> Don't want these? [unsubscribe] — one click, done.

---

## Touch 2 — day 3

**Subject:** re: estimates that went quiet

> [First] — the part most owners are surprised by is that the majority of these deals close on the
> fourth or fifth contact, not the first. Almost nobody gets that far, because you're busy running jobs.
>
> If you tell me roughly how many estimates go out a month, what share closes, and your average job
> value, I can show you what your own backlog is worth in about two minutes. No deck.
>
> [NAME] · [phone] · [address] · [unsubscribe]

---

## Touch 3 — day 8

**Subject:** the maths on [Company]'s unsold quotes

> [First],
>
> Say 40 estimates a month and a 25% close rate. That's 30 quotes a month going nowhere.
> Recovering even one of them at a typical [trade] job value pays for the whole engagement several
> times over.
>
> Those are illustrative figures — I'd rather run it on yours. Fifteen minutes?
>
> [NAME] · [phone] · [address] · [unsubscribe]

*(Note the wording: these numbers are labelled illustrative, because they are. Do not present them as a
client result until you have a client result.)*

---

## Touch 4 — day 15 — close the loop

**Subject:** closing the file

> [First] — I've not managed to catch you, so I'll assume the timing's wrong and stop emailing.
>
> If unsold estimates ever become the thing you want to fix, I'm on [phone].
>
> All the best,
> [NAME] · [address] · [unsubscribe]

The break-up email reliably pulls the highest reply rate in the sequence. That is *because* it is
genuine — so honour it. If they don't reply, stop. Don't restart the sequence in a month.

---

## After the sequence

Move them to `disqualified` with a reason, or leave `contacted` and try the phone. Never loop the
same person through the same emails again.

```
npm run pipeline -- touch <id> email --outcome no_reply
npm run pipeline -- move <id> disqualified --reason "4 touches, no reply"
```
