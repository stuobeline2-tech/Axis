// Render the free Denial Recovery Audit. Reports only what was computed from the client's file.
// Every limitation is printed. No industry benchmark appears without its source named inline.

const usd = n => '$' + (Math.round(n * 100) / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function renderAudit({ practice, summary, decision, ingestReport, asOf, preparedBy }) {
  const L = [];
  const p = s => L.push(s);
  const pl = (n, one, many) => `${n} ${n === 1 ? one : many}`;

  p(`# Denial Recovery Audit — ${practice}`);
  p('');
  p(`Prepared ${asOf} by ${preparedBy}. Computed entirely from the de-identified claims export you supplied.`);
  p('');
  p('## 1. What your file contains');
  p('');
  p(`| | |`);
  p(`|---|---|`);
  p(`| Denied claim lines analysed | ${summary.total_claims} |`);
  p(`| Total billed and not paid | **${usd(summary.total_denied_outstanding)}** |`);
  if (ingestReport?.rejected?.length) {
    p(`| Rows we could not read | ${ingestReport.rejected.length} — listed in §5 |`);
  }
  p('');
  p('## 2. What is still recoverable');
  p('');
  p('This is the number that matters, and it is smaller than the total above on purpose.');
  p('');
  p(`| Status | Claims | Value |`);
  p(`|---|---:|---:|`);
  p(`| **Still appealable — filing window confirmed open** | ${summary.counts.appealable} | **${usd(summary.confirmed_appealable_dollars)}** |`);
  p(`| Appealable, but we cannot confirm the filing window | ${summary.counts.window_unknown} | ${usd(summary.unknown_window_dollars)} |`);
  p(`| Filing window already expired — permanently lost | ${summary.counts.expired} | ${usd(summary.expired_dollars)} |`);
  p(`| Not appealable (patient responsibility, contractual, duplicate) | ${summary.counts.not_appealable} | ${usd(summary.not_appealable_dollars)} |`);
  p(`| Denial code not in our reference set — needs manual review | ${summary.counts.unknown_code} | ${usd(summary.unknown_code_dollars)} |`);
  p('');
  if (summary.expired_dollars > 0) {
    p(`> ${usd(summary.expired_dollars)} of your denied claims are past their filing deadline. That money `);
    p('> cannot be recovered by us or by anyone else. It is shown because you should know it, not');
    p('> because we can do anything about it.');
    p('');
  }
  if (summary.counts.window_unknown > 0) {
    p(`> ${pl(summary.counts.window_unknown, 'claim sits', 'claims sit')} with payers whose appeal window we have not documented.`);
    p('> We have **not** assumed a deadline for these — guessing one would either send you chasing dead');
    p('> claims or let live ones expire. Confirm the window from those payers\' provider manuals and');
    p('> they move into one of the two rows above.');
    p('');
  }

  p('## 3. Where the money is going');
  p('');
  p('| Denial code | What it means | Category | Claims | Value |');
  p('|---|---|---|---:|---:|');
  for (const c of summary.top_codes.slice(0, 10)) {
    p(`| ${c.code} | ${c.meaning ?? '_not in our reference set — manual review_'} | ${c.category} | ${c.count} | ${usd(c.dollars)} |`);
  }
  p('');

  p('## 4. Recommended worklist');
  p('');
  if (!summary.worklist.length) {
    p('_No appealable claims found in this file._');
  } else {
    p(`Top ${pl(summary.worklist.length, 'recoverable claim', 'recoverable claims')} by value.`);
    p('');
    p('| # | Claim ref | DOS | CPT | Payer | Code | Value | Days left | Action |');
    p('|---:|---|---|---|---|---|---:|---:|---|');
    summary.worklist.forEach((c, i) => {
      const dl = c.window.days_left === null ? '_unknown_' : c.window.days_left;
      p(`| ${i + 1} | ${c.claim_ref} | ${c.date_of_service} | ${c.procedure_code ?? ''} | ${c.payer ?? ''} | ${c.denial_code} | ${usd(c.outstanding)} | ${dl} | ${c.action} |`);
    });
  }
  p('');

  p('## 5. What this analysis could NOT determine');
  p('');
  p('- Whether any given appeal will be **paid**. That is the payer\'s decision. Nothing here predicts it.');
  p('- Whether a denial was **correct**. A claim can be appealable and still rightly denied on the merits.');
  p('- Anything requiring clinical documentation, which is not in a claims export.');
  if (summary.counts.unknown_code > 0) p(`- The meaning of ${pl(summary.counts.unknown_code, 'claim', 'claims')} whose denial code is outside our reference set.`);
  if (summary.counts.window_unknown > 0) p(`- The filing deadline for ${pl(summary.counts.window_unknown, 'claim', 'claims')} (see §2).`);
  if (ingestReport?.rejected?.length) {
    p(`- ${ingestReport.rejected.length} rows we could not parse:`);
    for (const r of ingestReport.rejected.slice(0, 20)) p(`  - row ${r.row}: ${r.reasons.join('; ')}`);
    if (ingestReport.rejected.length > 20) p(`  - …and ${ingestReport.rejected.length - 20} more`);
  }
  p('');
  p('## 6. What we recommend');
  p('');
  if (decision.may_sell) {
    p(`Your confirmed recoverable total is **${usd(decision.confirmed)}**. A 14-day Denial Recovery`);
    p(`Sprint at a flat **${usd(decision.price)}** would prepare appeal packets for the worklist above —`);
    p('appeal letter, payer appeal route and deadline, and the documentation checklist for each claim.');
    p('You submit them; we prepare them. Nothing in this recommendation promises a recovery amount.');
  } else {
    p(`**Our recommendation is that you do not buy anything.**`);
    p('');
    p(`Your confirmed recoverable total is ${usd(decision.confirmed)}, below the ${usd(decision.threshold)} we require`);
    p(`before selling a ${usd(decision.price)} Sprint. Paying us would not be worth it to you, so we are not offering it.`);
    p('');
    // Why the number is low matters. An unconfirmed window is not the same as a healthy denial rate,
    // and telling a practice their denials are "under control" on that basis would be false.
    if (summary.unknown_window_dollars > summary.confirmed_appealable_dollars) {
      p(`**But note why it is low.** ${usd(summary.unknown_window_dollars)} sits in ${pl(summary.counts.window_unknown, 'claim', 'claims')} we could not`);
      p('assess, because we have no documented appeal window for those payers — not because those claims');
      p('are unrecoverable. This is a gap on our side. Confirm those windows from the payers\' provider');
      p('manuals and the picture may change materially. **Do not read this as a clean bill of health.**');
    } else {
      p('Your denials appear to be reasonably under control. Keep the worklist above and work it in-house.');
    }
  }
  p('');
  p('---');
  p('');
  p('_Computed from your own claims export. No patient-identifying data was requested, received or stored._');
  p('_Denial code meanings are from the standard X12 CARC set; categories and recommended actions are our classification._');
  return L.join('\n') + '\n';
}
