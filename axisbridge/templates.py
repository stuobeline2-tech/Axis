"""
Outbound templates — VERBATIM as supplied in the brief.

Rules enforced elsewhere but stated here so nobody edits this file casually:
  * Bodies are sent exactly as written. Only {{double_brace}} variables are substituted.
  * No scheduling link is ever inserted. The only CTA is a reply.
  * Steps after 1 reply in-thread and carry NO subject — the thread subject persists.
  * The CAN-SPAM footer is appended by the renderer, not stored here.

The line breaks below are significant. Paragraphs are separated by a blank line; the two
questions in SEQUENCE_3 step 1 are on consecutive lines by design.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    step: int
    day: int
    body: str
    subject: str | None = None          # step 1 only
    reply_in_thread: bool = False


def _b(text: str) -> str:
    """Strip the leading/trailing newline the triple-quote literal adds. Nothing else."""
    return text.strip("\n")


SEQUENCE_1 = [
    Step(1, 0, subject="denied claims at {{practice_name}}", body=_b("""
Hi {{first_name}},

I run a billing company. We only work with mental health practices.

I am doing four free denial audits in {{state}} this month. I wanted to offer you one.

It works like this. You export your denied claims from the last 90 days. One of my certified billers works them. You keep every dollar we recover.

It costs nothing. You sign nothing except a BAA, which I send first.

Most practices we do this for are sitting on four to eight thousand dollars they already wrote off.

Want me to send the BAA over?

Anthony
Axisbridge Medical Staffing
""")),
    Step(2, 3, reply_in_thread=True, body=_b("""
Hi {{first_name}},

Following up on the free audit.

One thing I should have said. The most common denial we find in {{credential}} practices is {{denial_reason}}.

With {{payer}} it is usually a few thousand a quarter. It is completely fixable and most practices never see it, because nobody is working the denials.

Still happy to run yours. I just need a signed BAA and the claims export.

Anthony
""")),
    Step(3, 7, reply_in_thread=True, body=_b("""
Hi {{first_name}},

Quick question and then I will leave it.

When a claim gets denied at {{practice_name}}, who works it?

In most practices this size the honest answer is nobody, or eventually, me, at 9pm.

If that is the case here, the audit will find money. If you have someone on it properly, I will tell you that plainly and you will know your billing is in good shape.

Either way it costs nothing.

Anthony
""")),
    Step(4, 14, reply_in_thread=True, body=_b("""
Hi {{first_name}},

Last one from me on this.

Two of this month's four audit slots are gone. If you want the third I would need your claims report by Friday.

If the timing is wrong, that is completely fine. Keep my email. When your biller leaves — and at some point they do — we can have a trained replacement in your system in about a week.

That is really what we are here for.

Anthony
""")),
]

SEQUENCE_2 = [
    Step(1, 0, subject="first year billing at {{practice_name}}", body=_b("""
Hi {{first_name}},

Saw you started {{practice_name}} in {{city}} a while back. Congratulations — the first two years are the hard part.

I run a billing company that only works with mental health practices. Something I see constantly in the first two years:

Nobody set the billing up wrong on purpose. It just got set up fast, while you were busy getting patients. Then a pattern of small denials starts and nobody has time to look at it.

I will look at it for free. Send me your denied claims from the last 90 days. My biller works them. You keep everything we recover.

Want the BAA?

Anthony
Axisbridge Medical Staffing
""")),
    Step(2, 4, reply_in_thread=True, body=_b("""
Hi {{first_name}},

One thing worth knowing at your stage.

Most denials have a filing deadline. With {{payer}} it is often 90 or 180 days from date of service. After that the claim is dead and the money is gone permanently.

So the claims sitting in your denied bucket from last spring may still be recoverable. The ones from last year almost certainly are not.

That is the only reason I am following up. There is a clock on it.

Anthony
""")),
    Step(3, 9, reply_in_thread=True, body=_b("""
Hi {{first_name}},

Do you do your own billing right now?

No wrong answer. Plenty of practices at your stage do, and it works fine until the caseload gets to about twenty-five a week. Then the claims start going out late, and late claims get denied, and denied claims do not get worked because you are seeing patients.

If that sounds like where you are heading, the free audit will show you exactly where it is leaking.

Anthony
""")),
    Step(4, 16, reply_in_thread=True, body=_b("""
Hi {{first_name}},

Closing this out.

If it is useful, here is the one thing I would fix first, free of charge: verify eligibility on every patient before the session, not after. Not at intake — every session. Coverage changes mid-year and the practice finds out six weeks later when the claim bounces.

That single change stops the largest share of denials I see in practices your size.

Good luck with {{practice_name}}.

Anthony
""")),
]

SEQUENCE_3 = [
    Step(1, 0, subject="your billing company at {{practice_name}}", body=_b("""
Hi {{first_name}},

You almost certainly already have someone doing your billing. This is not a pitch to replace them.

I run a billing company for mental health practices. I am offering four free denial audits in {{state}} this month.

Here is why you might want one even though you are covered. Two questions:

Do they charge a flat fee or a percentage of collections?
Do they work your denials, or just submit clean claims?

Most do the second. That is where the money leaks.

Send me 90 days of denied claims. If your company is working them properly I will find nothing and tell you so. If there is money sitting there, you should know.

Anthony
Axisbridge Medical Staffing
""")),
    Step(2, 4, reply_in_thread=True, body=_b("""
Hi {{first_name}},

On the percentage question from my last note.

If your billing company takes 6% and you collect $80,000 a month, that is $4,800 a month. $57,600 a year.

That is not automatically bad. It depends entirely on whether they are working denials or only submitting claims. If they are only submitting, you are paying a percentage for the easy half of the job.

The audit tells you which one you are getting. Costs nothing either way.

Anthony
""")),
    Step(3, 10, reply_in_thread=True, body=_b("""
Hi {{first_name}},

One more and I will stop.

Ask your billing company for your denial rate and your first-pass acceptance rate for the last quarter.

If they send it back the same day, they are good and you should keep them. Genuinely.

If it takes a week or you get a vague answer, that tells you something too.

That test costs you one email and it is worth running whether or not you ever speak to me.

Anthony
""")),
]

SEQUENCE_4 = [   # trigger-based; enter within 48hrs of a job posting
    Step(1, 0, subject="your biller opening", body=_b("""
Hi {{first_name}},

Saw you are hiring a biller at {{practice_name}}.

Before you spend twelve weeks on that — I place trained mental health billers. Mine start in about seven days, inside your own system, on your hours.

You do no interviews and no training.

And because I know you are covering the gap yourself right now: send me the denied claims that have piled up since the seat went empty. My biller works them free and you keep everything we recover. That holds the line while you decide what to do.

Want the BAA?

Anthony
Axisbridge Medical Staffing
""")),
    Step(2, 5, reply_in_thread=True, body=_b("""
Hi {{first_name}},

One number worth having while you run that search.

A biller at $43,000 salary costs roughly $76,500 a year once you add payroll tax, benefits, recruitment and the turnover that hits about every eighteen months.

And in twelve to eighteen months you will most likely be writing that job post again.

Not asking for anything. The free audit offer stands whether you hire locally or not.

Anthony
""")),
    Step(3, 21, reply_in_thread=True, body=_b("""
Hi {{first_name}},

How is the search going?

Three weeks in is usually where practices find out the good candidates want more than the posting offers, and the ones who will take it have never touched a mental health claim.

If you are there, mine can start in a week and there is a trained backup assigned to your practice from day one. If you have found someone, genuinely well done — keep my email for next time.

Anthony
""")),
]

SEQUENCE_5 = [
    Step(1, 0, subject="{{clinician_count}} clinicians at {{practice_name}}", body=_b("""
Hi {{first_name}},

Looked at {{practice_name}} — {{clinician_count}} clinicians in {{city}}.

At that size you are submitting a lot of claims a month. Which means even a 5% denial rate is real money, and denials at that volume are a full-time job on their own.

I place trained mental health billers with group practices. But before any of that, I would rather just show you.

Send me 90 days of denied claims. My biller works them. You keep everything we recover. No cost, no contract, BAA first.

Worth a look?

Anthony
Axisbridge Medical Staffing
""")),
    Step(2, 5, reply_in_thread=True, body=_b("""
Hi {{first_name}},

The thing that usually matters most at your size is not cost. It is coverage.

One biller for {{clinician_count}} clinicians means one person's holiday stops your revenue for two weeks. One resignation stops it for three months.

Every placement I make comes with a second trained biller assigned to that practice from day one. Not a promise to find cover — an actual named person who already knows the account.

The free audit stands either way. Want it?

Anthony
""")),
    Step(3, 12, reply_in_thread=True, body=_b("""
Hi {{first_name}},

If you are not the right person for this, would you point me to whoever owns billing at {{practice_name}}?

Happy to go direct and stop filling your inbox.

And the offer is the same for them — 90 days of denied claims worked free, you keep the recoveries.

Anthony
""")),
]

SEQUENCE_6 = [   # non-repliers only, 90+ days after their sequence ended
    Step(1, 0, subject="quarterly denial pattern — {{state}} practices", body=_b("""
Hi {{first_name}},

We finished audits for a set of mental health practices in {{state}} this quarter. One pattern showed up in nearly all of them.

{{denial_reason}} against {{payer}}. Small amounts, every single month, never worked, and invisible unless somebody is specifically looking for it.

I am running four more free audits this month. You send 90 days of denied claims, my biller works them, you keep everything recovered.

If your billing is clean I will tell you that and you will have lost nothing.

Anthony
Axisbridge Medical Staffing
""")),
    Step(2, 6, reply_in_thread=True, body=_b("""
Hi {{first_name}},

One more thing from those audits.

The practices that had the least money sitting in denials all had one habit in common. Somebody checked the denial report every single week, not every month.

Monthly is too slow. Timely filing deadlines start closing before you have looked.

If nobody is doing that weekly at {{practice_name}}, my audit will find it. Free, and you keep whatever we recover.

Anthony
""")),
]

SEQUENCES = {
    "SEQUENCE_1": SEQUENCE_1, "SEQUENCE_2": SEQUENCE_2, "SEQUENCE_3": SEQUENCE_3,
    "SEQUENCE_4": SEQUENCE_4, "SEQUENCE_5": SEQUENCE_5, "SEQUENCE_6": SEQUENCE_6,
}

# ---------------------------------------------------------------------------------
# PHASE 3 reply templates. Only the ones supplied in the brief are here.
# The brief says "exactly one of the five templates below" but the message was
# truncated partway through REPLY_C. REPLY_C is stored TRUNCATED and marked
# incomplete; REPLY_D and REPLY_E were never received. They are NOT invented — an
# invented auto-reply to a practice asking about HIPAA or pricing is exactly the
# failure mode the brief's own "never invent an answer" rule exists to prevent.
# Any reply that would have matched C/D/E falls through to human escalation.
# ---------------------------------------------------------------------------------
REPLY_A = _b("""
Signed BAA attached — one page, takes a minute.

For the claims: in your EHR there is a denied claims or rejected claims report. Run it for the last 90 days and export it. That is the whole thing.

Send it back here and you will have results within 72 hours.

Anthony
""")

REPLY_B = _b("""
Fair question.

HIPAA is about how data is handled, not where the person sits. We sign a BAA before anyone touches a claim — I send it before the free audit, not after.

Your biller works through your own system, with logged access and nothing stored locally. HHS permits offshore business associates where the BAA is in place.

You will have more visibility into my biller than most practices have over in-house staff.

Still want the audit?

Anthony
""")

REPLY_C_TRUNCATED = _b("""
Most practices I write to do.

Two questions — flat fee or percentage, and do they work your denials or only submit claims?

Let me run the free audit anyway. If they are working your denials properly I will find nothing and tell you plainly, and you will know they are doing a good job
""")

REPLIES = {"REPLY_A": REPLY_A, "REPLY_B": REPLY_B}

INCOMPLETE_REPLIES = {
    "REPLY_C": "truncated mid-sentence in the brief — last words received: '...you will know they are doing a good job'",
    "REPLY_D": "never received",
    "REPLY_E": "never received",
}
