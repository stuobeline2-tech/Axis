# Legitimate Interests Assessment — NPPES prospect dataset
Controller: the operator (UK). Prepared 2026-08-16. Review date: 2027-02-16.
Status: **prospective** — the dataset is not held in this session (egress-blocked). This LIA must
be in place *before* any record is ingested, not after.

## 1. The dataset
NPPES (National Plan and Provider Enumeration System), published by the US Centers for Medicare &
Medicaid Services as a public record of healthcare providers holding an NPI. Fields used:
organisation/provider name, NPI, taxonomy (specialty), practice address, practice telephone.
Individual practitioners' names are personal data; organisational records may not be.

## 2. Purpose test — is there a legitimate interest?
Yes. Direct marketing of a business service to businesses whose published function makes the
service relevant to their role. The ICO accepts direct marketing as capable of being a legitimate
interest. Our interest: finding practices that plausibly have recoverable denied claims.
Third-party benefit: the practice recovers money it has already earned.

## 3. Necessity test
Is processing necessary to achieve it? Yes, and it is the least intrusive route available: NPPES
is the authoritative public register of exactly the population we need, published for public use.
The alternative — buying enriched contact lists — would involve *more* personal data, of lower
provenance, and is separately excluded (see `shariah/c23.md`). We process the minimum fields
needed to identify and contact a practice in its business capacity. **No special category data.
No patient data. Ever.**

## 4. Balancing test
- **Reasonable expectations:** providers publish these details on a public register precisely so
  they can be contacted in a professional capacity. Receiving a relevant B2B approach is within
  reasonable expectation.
- **Relationship:** none prior. This weighs against us and is why relevance is enforced: only
  practice types where denial recovery is genuinely applicable are contacted.
- **Intrusiveness:** low. Business address and business phone, business email where independently
  and lawfully obtained. No home addresses, no personal mobiles, no personal social profiles.
- **Harm:** low. Worst case is an unwanted but relevant business email carrying a working opt-out.
- **Safeguards:** suppression checked at send time; opt-out honoured immediately and permanently;
  volume capped; no more than the drafted follow-up sequence; sender identified with a genuine
  postal address; retention limited.
- **Conclusion:** legitimate interests is available and is not overridden. **Balance: passes.**

## 5. Retention
- Not contacted: 12 months from ingest, then deleted.
- Contacted, no reply: 12 months from last contact, then deleted.
- Opted out: contact identifier retained **indefinitely on the suppression list only** — this is
  necessary to honour the objection and is itself the safeguard, not a marketing retention.
- Became a customer: retained under the customer relationship, separate basis (contract).

## 6. Data subject rights
Right to object is absolute for direct marketing (UK GDPR Art. 21(2)) — honoured immediately, no
questions asked, no "are you sure" step. Art. 14 privacy information is provided by a link in
every message to a published privacy notice. Access/erasure requests honoured within one month.

## 7. Cross-border note
Data subjects are in the US. UK GDPR applies to us as controller regardless. CAN-SPAM applies to
the recipients: genuine physical postal address, no deceptive headers or subject lines, clear
opt-out honoured within 10 business days (we honour immediately, which exceeds it).

## 8. Outstanding before first send
- [ ] Privacy notice published at a live URL, linked in every message
- [ ] Postal address confirmed for the footer
- [ ] Suppression list live and checked at send time
- [ ] Retention deletion job scheduled
