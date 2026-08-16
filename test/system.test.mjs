import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { ingest, IngestRefusal, normaliseDenialCode } from '../system/ingest/ingest.mjs';
import { classify, summarise, sellDecision, outstanding, windowStatus } from '../system/score/appealability.mjs';
import { renderAudit } from '../system/generate/audit.mjs';
import { computeFunnel } from '../system/dashboard/funnel.mjs';
import { runPresend } from '../system/outbound/presend.mjs';

const FIXTURE = readFileSync(new URL('./fixtures/sample-denials.csv', import.meta.url), 'utf8');
const WINDOWS = { default_days: null, payers: {
  'Payer A': { appeal_window_days: 180, source: 'TEST FIXTURE — not a real payer policy' },
  'Payer B': { appeal_window_days: 60,  source: 'TEST FIXTURE — not a real payer policy' },
} };

test('ingest refuses an export containing patient identifiers', () => {
  const csv = 'Patient Name,Date of Service,CPT,Payer,Denial Code,Billed Amount\nJ Doe,2026-01-01,90837,P,CO-50,100\n';
  assert.throws(() => ingest(csv), e => e instanceof IngestRefusal && /identifier column/i.test(e.message));
});

test('ingest refuses DOB and member ID specifically', () => {
  const forbidden = ['DOB', 'Patient DOB', 'Date of Birth', 'Member ID', 'Subscriber ID', 'MRN',
                     'Medical Record Number', 'SSN', 'Patient Address', 'Patient Name', 'Last Name',
                     'Patient Zip', 'Home Phone', 'Patient Email', 'Guarantor Name', 'Policy Number'];
  for (const col of forbidden) {
    const csv = `${col},Date of Service,CPT,Payer,Denial Code,Billed Amount\nx,2026-01-01,90837,P,CO-50,100\n`;
    assert.throws(() => ingest(csv), IngestRefusal, `${col} should be refused`);
  }
});

test('ingest refuses a file missing required columns', () => {
  assert.throws(() => ingest('Date of Service,CPT\n2026-01-01,90837\n'),
    e => e instanceof IngestRefusal && /required column/i.test(e.message));
});

test('ingest parses US dates, currency symbols and parenthesised negatives', () => {
  const { claims } = ingest('Date of Service,CPT,Payer,Denial Code,Billed Amount,Paid Amount\n3/4/26,90837,Aetna,CO-197,"$1,250.50",(25.00)\n');
  assert.equal(claims[0].date_of_service, '2026-03-04');
  assert.equal(claims[0].billed_amount, 1250.5);
  assert.equal(claims[0].paid_amount, -25);
});

test('ingest quarantines unparseable rows instead of dropping them silently', () => {
  const { claims, rejected } = ingest('Date of Service,CPT,Payer,Denial Code,Billed Amount\nnot-a-date,90837,P,CO-50,100\n2026-01-01,90837,P,CO-50,100\n');
  assert.equal(claims.length, 1);
  assert.equal(rejected.length, 1);
  assert.match(rejected[0].reasons.join(), /date_of_service/);
});

test('denial codes normalise across CO-/PR-/spacing variants', () => {
  for (const [raw, want] of [['CO-197','197'], ['co197','197'], ['PR 1','1'], ['CO-B7','B7'], ['45','45']])
    assert.equal(normaliseDenialCode(raw), want, raw);
});

test('outstanding is billed minus paid, never negative', () => {
  assert.equal(outstanding({ billed_amount: 285, paid_amount: 50 }), 235);
  assert.equal(outstanding({ billed_amount: 100, paid_amount: 150 }), 0);
  assert.equal(outstanding({ billed_amount: null }), 0);
});

test('an undocumented payer yields window_unknown — never an assumed deadline', () => {
  const w = windowStatus({ payer: 'Nobody', date_of_service: '2026-01-01' }, WINDOWS, '2026-08-16');
  assert.equal(w.status, 'window_unknown');
  assert.equal(w.days_left, null);
});

test('documented windows classify open and expired correctly', () => {
  const open = windowStatus({ payer: 'Payer A', last_action_date: '2026-07-01' }, WINDOWS, '2026-08-16');
  assert.equal(open.status, 'open');
  assert.equal(open.counted_from, 'last_action_date');
  const gone = windowStatus({ payer: 'Payer B', last_action_date: '2026-02-01' }, WINDOWS, '2026-08-16');
  assert.equal(gone.status, 'expired');
});

test('patient-responsibility and duplicate codes are never put on the worklist', () => {
  const { claims } = ingest(FIXTURE);
  const s = summarise(classify(claims, { asOf: '2026-08-16', windows: WINDOWS }));
  const refs = s.worklist.map(c => c.claim_ref);
  assert.ok(!refs.includes('SYNTH-004'), 'PR-1 deductible must not be on the worklist');
  assert.ok(!refs.includes('SYNTH-010'), 'CO-18 duplicate must not be on the worklist');
});

test('an unrecognised denial code is reported as unknown, not guessed', () => {
  const { claims } = ingest(FIXTURE);
  const c = classify(claims, { asOf: '2026-08-16', windows: WINDOWS }).find(x => x.claim_ref === 'SYNTH-013');
  assert.equal(c.disposition, 'unknown_code');
  assert.equal(c.code_meaning, null);
  assert.equal(c.category, 'unknown');
});

test('worklist is ordered by dollars descending and capped at 40', () => {
  const { claims } = ingest(FIXTURE);
  const s = summarise(classify(claims, { asOf: '2026-08-16', windows: WINDOWS }));
  const vals = s.worklist.map(c => c.outstanding);
  assert.deepEqual(vals, [...vals].sort((a, b) => b - a));
  assert.ok(s.worklist.length <= 40);
});

test('GUARANTEE 1: the Sprint is refused below 5x the fee', () => {
  const { claims } = ingest(FIXTURE);
  const s = summarise(classify(claims, { asOf: '2026-08-16', windows: WINDOWS }));
  const d = sellDecision(s);
  assert.equal(d.threshold, 7500);
  assert.equal(d.may_sell, false, 'fixture totals ~$3.7k and must not be sellable');
  assert.match(d.reason, /DO NOT SELL/);
});

test('GUARANTEE 1: the Sprint is permitted once confirmed value clears the threshold', () => {
  const d = sellDecision({ confirmed_appealable_dollars: 9000, unknown_window_dollars: 0 });
  assert.equal(d.may_sell, true);
});

test('unknown-window dollars can NEVER push a practice over the sell threshold', () => {
  const d = sellDecision({ confirmed_appealable_dollars: 100, unknown_window_dollars: 50_000 });
  assert.equal(d.may_sell, false, 'a config gap must not manufacture a sale');
  assert.match(d.reason, /not a reason to sell/);
});

test('the audit prints what it could not determine, and never promises recovery', () => {
  const { claims, ...rest } = ingest(FIXTURE);
  const s = summarise(classify(claims, { asOf: '2026-08-16', windows: WINDOWS }));
  const md = renderAudit({ practice: 'Fixture Practice', summary: s, decision: sellDecision(s),
                           ingestReport: rest, asOf: '2026-08-16', preparedBy: 'test' });
  assert.match(md, /could NOT determine/);
  assert.match(md, /That is the payer's decision/);
  assert.match(md, /do not buy anything/i, 'below threshold, the audit must say do not buy');
  assert.doesNotMatch(md, /we (?:typically )?recover \d/i);
  assert.doesNotMatch(md, /guarantee[d]? (?:a )?recovery/i);
});

test('funnel reports null — not zero — when no real events exist', () => {
  const f = computeFunnel('event_id,ts,prospect_id,stage,amount_gbp,cost_gbp,fulfilment_hours,note\n');
  assert.equal(f.rows, 0);
  assert.equal(f.revenue_gbp, null);
  assert.equal(f.profit_per_human_hour, null);
  assert.equal(f.conversions.replied, null);
  assert.match(f.note, /not because it is zero/);
});

test('funnel computes real conversions from real rows', () => {
  const csv = 'event_id,ts,prospect_id,stage,amount_gbp,cost_gbp,fulfilment_hours,note\n'
    + '1,2026-08-01T09:00:00Z,p1,contacted,,0.10,,\n'
    + '2,2026-08-01T09:00:00Z,p2,contacted,,0.10,,\n'
    + '3,2026-08-02T09:00:00Z,p1,replied,,,,\n'
    + '4,2026-08-05T09:00:00Z,p1,paid,1200,,5,\n';
  const f = computeFunnel(csv);
  assert.equal(f.stages.contacted, 2);
  assert.equal(f.conversions.replied, 50);
  assert.equal(f.revenue_gbp, 1200);
  assert.equal(f.revenue_per_human_hour, 240);
});

// --- pre-send gate ---
function gateFixture(artifact, { prospect, suppression = 'identifier,identifier_type,added_at,reason,source\n' } = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'presend-'));
  const outbox = join(dir, 'outbox'); const lia = join(dir, 'lia');
  require_mkdir(outbox); require_mkdir(lia);
  writeFileSync(join(lia, 'lia-nppes.md'), '# LIA');
  writeFileSync(join(outbox, 'a.json'), JSON.stringify(artifact));
  const pPath = join(dir, 'prospects.csv');
  writeFileSync(pPath, 'contact_email,source_url,retrieved_at,pecr_class,source_dataset\n' + prospect);
  const sPath = join(dir, 'sup.csv'); writeFileSync(sPath, suppression);
  return runPresend({ outboxDir: outbox, prospectsPath: pPath, suppressionPath: sPath, liaDir: lia,
    sender: { senderName: 'A Operator', senderEntity: 'Axisbridge Medical Staffing Ltd', postalAddress: '1 Example Street, London' } });
}
function require_mkdir(d) { import('node:fs').then(fs => {}); require('node:fs').mkdirSync(d, { recursive: true }); }
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

const GOOD_BODY = 'Hi — noticed something specific about your practice.\n\nA Operator, Axisbridge Medical Staffing Ltd\n1 Example Street, London\nPrivacy notice: https://example.invalid/privacy\nTo unsubscribe, reply STOP and you will be removed permanently.';
const GOOD_PROSPECT = 'doc@example.invalid,https://npiregistry.example/1,2026-08-16T10:00:00Z,corporate_subscriber,nppes\n';

test('pre-send passes a complete, compliant artifact', () => {
  const r = gateFixture({ to: 'doc@example.invalid', subject: 'Denied claims at your practice', body: GOOD_BODY }, { prospect: GOOD_PROSPECT });
  assert.deepEqual(r.problems, []);
  assert.equal(r.ok, true);
});

test('pre-send blocks a suppressed recipient', () => {
  const r = gateFixture({ to: 'doc@example.invalid', subject: 'S', body: GOOD_BODY },
    { prospect: GOOD_PROSPECT, suppression: 'identifier,identifier_type,added_at,reason,source\ndoc@example.invalid,email,2026-08-01,opt-out,reply\n' });
  assert.equal(r.ok, false);
  assert.ok(r.problems.some(p => /check 3/.test(p)));
});

test('pre-send blocks a sole trader on PECR grounds', () => {
  const r = gateFixture({ to: 'doc@example.invalid', subject: 'S', body: GOOD_BODY },
    { prospect: 'doc@example.invalid,https://x.invalid/1,2026-08-16T10:00:00Z,sole_trader,nppes\n' });
  assert.equal(r.ok, false);
  assert.ok(r.problems.some(p => /check 11/.test(p) && /consent/.test(p)));
});

test('pre-send blocks a missing unsubscribe, missing address and placeholder text', () => {
  const r = gateFixture({ to: 'doc@example.invalid', subject: 'S', body: 'Hi {{first_name}}, A Operator' }, { prospect: GOOD_PROSPECT });
  assert.equal(r.ok, false);
  for (const n of [4, 6, 7, 10]) assert.ok(r.problems.some(p => new RegExp(`check ${n}`).test(p)), `check ${n} should fail`);
});

test('pre-send blocks a performance claim with no source marker, and allows a sourced one', () => {
  const bad = gateFixture({ to: 'doc@example.invalid', subject: 'S', body: GOOD_BODY + '\nWe recovered 40% for clients.' }, { prospect: GOOD_PROSPECT });
  assert.ok(bad.problems.some(p => /check 9/.test(p)));
  const good = gateFixture({ to: 'doc@example.invalid', subject: 'S', body: GOOD_BODY + '\nIndustry initial denial rates average 11.8% [src: qualigenix.com/claim-denials-2026].' }, { prospect: GOOD_PROSPECT });
  assert.deepEqual(good.problems, []);
});

test('pre-send blocks a recipient absent from prospects.csv', () => {
  const r = gateFixture({ to: 'stranger@example.invalid', subject: 'S', body: GOOD_BODY }, { prospect: GOOD_PROSPECT });
  assert.ok(r.problems.some(p => /check 1/.test(p)));
});

test('pre-send blocks a deceptive Re: subject prefix', () => {
  const r = gateFixture({ to: 'doc@example.invalid', subject: 'Re: our conversation', body: GOOD_BODY }, { prospect: GOOD_PROSPECT });
  assert.ok(r.problems.some(p => /check 8/.test(p)));
});

test('a low total caused by undocumented windows is NOT reported as healthy denials', () => {
  const { claims, ...rest } = ingest(FIXTURE);
  // no payer windows configured at all -> everything lands in window_unknown
  const s = summarise(classify(claims, { asOf: '2026-08-16', windows: { default_days: null, payers: {} } }));
  const md = renderAudit({ practice: 'P', summary: s, decision: sellDecision(s), ingestReport: rest,
                           asOf: '2026-08-16', preparedBy: 'test' });
  assert.match(md, /note why it is low/);
  assert.match(md, /Do not read this as a clean bill of health/);
  assert.doesNotMatch(md, /reasonably under control/,
    'must not claim denials are under control when the cause is our own missing config');
});

test('a genuinely low total IS reported as denials under control', () => {
  const summary = { total_claims: 3, total_denied_outstanding: 400, confirmed_appealable_dollars: 400,
    unknown_window_dollars: 0, expired_dollars: 0, not_appealable_dollars: 0, unknown_code_dollars: 0,
    counts: { appealable: 3, window_unknown: 0, expired: 0, not_appealable: 0, unknown_code: 0 },
    top_codes: [], worklist: [] };
  const md = renderAudit({ practice: 'P', summary, decision: sellDecision(summary), ingestReport: { rejected: [] },
                           asOf: '2026-08-16', preparedBy: 'test' });
  assert.match(md, /reasonably under control/);
});

test('singular claim counts read as "1 claim", not "1 claims"', () => {
  const { claims, ...rest } = ingest(FIXTURE);
  const s = summarise(classify(claims, { asOf: '2026-08-16', windows: WINDOWS }));
  const md = renderAudit({ practice: 'P', summary: s, decision: sellDecision(s), ingestReport: rest,
                           asOf: '2026-08-16', preparedBy: 'test' });
  assert.doesNotMatch(md, /\b1 claims\b/);
});
