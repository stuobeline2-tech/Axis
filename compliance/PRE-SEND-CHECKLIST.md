# PRE-SEND CHECKLIST — must pass before the §1.1 Send gate is opened

Run `node system/outbound/presend.mjs --outbox outbox/` . It **exits non-zero** if any check
fails. It is not advisory: it is the gate.

| # | Check | Enforced by |
|---|---|---|
| 1 | Every artifact has a `to` that appears in `data/prospects.csv` | code |
| 2 | Every prospect row has a non-empty `source_url` and a parseable `retrieved_at` | code |
| 3 | No recipient appears on `compliance/suppression.csv` (checked **now**, at send time) | code |
| 4 | Every message contains a working unsubscribe instruction | code |
| 5 | Every message identifies the sender by name and legal entity | code |
| 6 | Every message contains a genuine physical postal address (CAN-SPAM) | code |
| 7 | Every message links the published privacy notice (UK GDPR Art. 14) | code |
| 8 | Subject line is not deceptive — no fake `Re:`/`Fwd:`, no false urgency | code |
| 9 | No message contains a performance claim that is not traceable to a real logged outcome or a cited source | code |
| 10 | No message contains placeholder text (`{{`, `TODO`, `XXX`, `Lorem`) | code |
| 11 | Recipient segmentation recorded: corporate subscriber vs sole trader / individual (PECR) | code |
| 12 | An LIA exists for the dataset the recipient came from | code |
| 13 | Volume within the stated cap | code |
| 14 | Human operator has read and approved the batch | **human — cannot be automated** |

Check 14 is the Send gate itself. Checks 1–13 exist so that the human review in 14 is about
judgement and copy, not about compliance mechanics.

## PECR segmentation rule (check 11)
- **Corporate subscriber** (limited company, LLP, public body, Scottish partnership): unsolicited
  B2B electronic mail permitted without prior consent, with identification and opt-out.
- **Sole trader, individual, unincorporated partnership**: treated as an individual subscriber —
  **consent required**. These rows are not sent to. They are not "B2B by default".
- Where entity type cannot be established from the source, the row is treated as an individual
  subscriber. Fail closed.
