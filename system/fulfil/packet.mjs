// Appeal packet per claim — the paid Sprint deliverable.
// Deliberately leaves payer-specific routing as an explicit TO BE CONFIRMED rather than inventing it:
// an invented appeals address or deadline would be acted on by the practice.

const usd = n => '$' + (Math.round(n * 100) / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const DOCS = {
  authorisation: ['Copy of the authorisation/referral if one was obtained', 'If none was obtained: the clinical rationale for urgent/emergent treatment', 'Payer policy section relied on'],
  medical_necessity: ['Relevant clinical notes for the date of service', 'The payer\'s own medical policy for this CPT', 'Statement mapping the documentation to each policy criterion'],
  coding: ['Corrected claim with the appropriate modifier or diagnosis linkage', 'Coding rationale citing the CPT/ICD guideline relied on'],
  timely_filing: ['Proof of original timely submission — clearinghouse acceptance report or payer acknowledgement with date', 'Explanation of any intervening rejection'],
  bundling: ['CCI edit rationale and the modifier basis for separate reporting', 'Documentation showing the services were distinct'],
  eligibility: ['Eligibility verification captured on or before the date of service', 'Any coordination-of-benefits information held'],
  coverage: ['Member\'s benefit summary for the plan year', 'Payer policy showing the service is a covered benefit'],
  routing: ['Correct payer identification for the date of service', 'Corrected claim submitted to the correct payer'],
  credentialing: ['Provider enrolment/effective-date confirmation with the payer', 'CAQH attestation date'],
  administrative: ['The specific missing element identified on the remittance', 'Corrected claim'],
};

export function renderPacket(claim, { practice, preparedBy, asOf, payerRouting = {} }) {
  const route = payerRouting[claim.payer] ?? null;
  const docs = DOCS[claim.category] ?? ['Documentation supporting the service as billed'];
  const corrected = claim.action === 'corrected_resubmission';
  const L = [];
  const p = s => L.push(s);

  p(`# ${corrected ? 'Corrected resubmission' : 'Appeal'} — claim ${claim.claim_ref}`);
  p('');
  p(`Practice: ${practice} · Prepared ${asOf} by ${preparedBy}`);
  p('');
  p('| | |');
  p('|---|---|');
  p(`| Date of service | ${claim.date_of_service} |`);
  p(`| Procedure | ${claim.procedure_code ?? '—'} |`);
  p(`| Payer | ${claim.payer ?? '—'} |`);
  p(`| Denial code | ${claim.denial_code} — ${claim.code_meaning ?? '_not in reference set_'} |`);
  p(`| Amount outstanding | **${usd(claim.outstanding)}** |`);
  p(`| Filing window | ${claim.window.status === 'open' ? `${claim.window.days_left} days remaining (counted from ${claim.window.counted_from})` : claim.window.status === 'expired' ? 'EXPIRED — do not submit' : 'NOT DOCUMENTED — confirm before submitting'} |`);
  p('');

  if (claim.window.status === 'expired') {
    p('> **Do not submit this appeal.** The filing window has passed. Included only so the loss is visible.');
    p('');
    return L.join('\n') + '\n';
  }

  p('## 1. Where to send it');
  p('');
  if (route) {
    p(`- Route: ${route.route}`);
    p(`- Deadline: ${route.deadline}`);
    p(`- Source: ${route.source}`);
  } else {
    p(`- **TO BE CONFIRMED by the practice.** We have not documented ${claim.payer ?? 'this payer'}'s appeal route.`);
    p('- Take it from the payer\'s current provider manual or the remittance advice itself. We have not');
    p('  guessed an address or a deadline, because a wrong one costs you the claim.');
  }
  p('');

  p('## 2. Attach these');
  p('');
  for (const d of docs) p(`- [ ] ${d}`);
  p('- [ ] Copy of the original claim as submitted');
  p('- [ ] Copy of the remittance advice showing the denial');
  p('');

  p('## 3. Draft letter');
  p('');
  p('> To the Appeals Department,');
  p('>');
  p(`> We are requesting reconsideration of claim ${claim.claim_ref} for date of service ${claim.date_of_service},`);
  p(`> procedure ${claim.procedure_code ?? '[CPT]'}, denied under adjustment reason code ${claim.denial_code}`);
  p(`> (${claim.code_meaning ?? 'see remittance'}). The amount at issue is ${usd(claim.outstanding)}.`);
  p('>');
  if (corrected) {
    p('> The claim is resubmitted corrected as described in the attached coding rationale. We ask that the');
    p('> corrected claim be adjudicated on its merits.');
  } else {
    p('> We believe the denial should be reconsidered on the basis of the enclosed documentation, which');
    p('> addresses the specific reason given. **[Practice: state in one or two sentences why the denial is');
    p('> incorrect for THIS claim, referring to the attached documents. Do not send this letter without');
    p('> completing this paragraph — a generic appeal is the most common reason an appeal fails.]**');
  }
  p('>');
  p('> Please confirm receipt and advise the determination timeframe.');
  p('>');
  p(`> ${practice}`);
  p('');
  p('## 4. Before sending');
  p('');
  p('- [ ] The paragraph above is specific to this claim, not generic');
  p('- [ ] Every attachment in §2 is present');
  p('- [ ] Submitted inside the filing window');
  p('');
  p('_Prepared for submission by the practice. We do not submit on your behalf._');
  return L.join('\n') + '\n';
}
