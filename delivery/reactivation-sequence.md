# 5-touch reactivation sequence

Sent to the **client's own** prior estimate contacts, under the **client's** brand, with their approval.
These people asked this contractor for a price. That prior relationship is what makes contact appropriate.

## Boundaries

- **Never send this to a purchased or scraped list.** Only people who requested a quote.
- **Honour opt-outs instantly**, across every channel, permanently.
- **SMS carries legal weight** (TCPA in the US). Send from the client's own number/messaging
  platform, with their documented consent basis. If the client can't evidence the relationship,
  email only.
- **Business hours only**, recipient's local time. No weekends, no evenings.
- **No fake personalisation.** Don't write "I was thinking about your project" if nobody was.

---

## Touch 1 — day 0 — SMS

> Hi [First], it's [Client Business] — we quoted you for [job] back in [month].
> Just checking whether you still need it doing, or if you've sorted it already?
> Either answer's fine, just don't want to leave you hanging. — [Owner]

Short, no pitch, easy to answer either way. "Or if you've sorted it" gives permission to say no,
which is what makes people reply at all.

## Touch 2 — day 3 — Email

**Subject:** your [job type] quote — still needed?

> Hi [First],
>
> We sent you a quote on [date] for [job] and haven't heard back — which usually means one of three
> things: the timing wasn't right, the price wasn't right, or life got busy.
>
> Any of those is fine. If it's the price, tell me — there's sometimes a way to stage the work.
> If it's timing, tell me roughly when and I'll get out of your way until then.
>
> [Owner], [Client Business]
> [phone] · [address] · [unsubscribe]

Naming the objections out loud is what unsticks these. Most never get asked.

## Touch 3 — day 8 — SMS

> [First] — [Owner] at [Client Business]. Has [job] been taken care of?
> If you'd like me to take another look at the numbers I'm happy to. If you've moved on, just say
> and I'll close the file.

## Touch 4 — day 15 — Email — the useful one

**Subject:** one thing worth knowing before you book [job type]

> Hi [First],
>
> Whether or not you use us, one thing worth knowing on [job type]: [genuine, specific, useful advice —
> what to check, what most quotes leave out, what goes wrong in [season]].
>
> If you'd like us to revisit the quote, reply and I'll sort it. If not, no hard feelings —
> hopefully that's useful either way.
>
> [Owner] · [phone] · [address] · [unsubscribe]

**This touch must contain real advice**, written with the contractor's actual expertise. It is the
highest-performing message in the sequence *because* it gives something away. A hollow version
of this email is worse than not sending it.

## Touch 5 — day 24 — SMS — close the file

> [First], closing out our file on [job] so we stop bothering you.
> If it comes back around, we're on [phone]. All the best — [Owner]

Then **stop.** Do not restart. Do not "re-engage" in 90 days. Closing the file means closing the file.

---

## Logging

Every reply goes in `attribution-log.csv` the day it happens:

| outcome | meaning |
|---|---|
| `booked` | appointment scheduled — hand to client same day |
| `interested_later` | genuine future intent, with a date |
| `price_objection` | wants the number revisited — client's call |
| `already_done` | went elsewhere or did it themselves |
| `no` | not interested — remove from all future contact |
| `opt_out` | explicit stop request — permanent, all channels |
| `no_reply` | five touches, silence |

`already_done` is worth counting honestly: a high rate of it means the client is losing work to
speed, not to follow-up, and you should tell them that even though it isn't what you sell.
