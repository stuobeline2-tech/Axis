import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scoreLead } from '../lead-engine/score.mjs';
import { MIN_TICKET } from '../lead-engine/trades.mjs';

const base = { rating: 4.5, reviewCount: 100, website: 'https://x.com' };

test('a strong roofing lead scores highly and is a fit', () => {
  const r = scoreLead({ ...base, trade: 'roofing', reviewCount: 200 });
  assert.ok(r.score >= 90, `expected >=90, got ${r.score}`);
  assert.equal(r.fit, true);
});

test('low-ticket trades are rejected outright, whatever else is true', () => {
  for (const trade of ['handyman', 'cleaning', 'pest']) {
    const r = scoreLead({ ...base, trade, reviewCount: 5000, rating: 4.5 });
    assert.equal(r.fit, false, `${trade} should never be a fit`);
    assert.equal(r.score, 0);
    assert.match(r.reasons[0], /below the \$[\d,]+ floor/);
  }
});

test('the ticket floor matches the calculator finding that the fee cannot pay back', () => {
  // A $1,000/mo fee against ~5% recovery needs roughly $2.5k jobs to clear.
  assert.equal(MIN_TICKET, 2500);
  const justUnder = scoreLead({ ...base, trade: 'roofing', avgTicket: MIN_TICKET - 1 });
  const justOver  = scoreLead({ ...base, trade: 'roofing', avgTicket: MIN_TICKET });
  assert.equal(justUnder.fit, false);
  assert.equal(justOver.fit, true);
});

test('an explicit avgTicket overrides the trade default', () => {
  const r = scoreLead({ ...base, trade: 'roofing', avgTicket: 500 });
  assert.equal(r.fit, false, 'a roofer quoting $500 jobs is still not a fit');
});

test('no website costs points and is called out', () => {
  const withSite = scoreLead({ ...base, trade: 'hvac' });
  const without  = scoreLead({ ...base, trade: 'hvac', website: null });
  assert.equal(withSite.score - without.score, 15);
  assert.ok(without.reasons.some(x => /no website/.test(x)));
});

test('a 5.0 rating on 3 reviews is treated as noise, not excellence', () => {
  const suspicious = scoreLead({ trade: 'roofing', rating: 5.0, reviewCount: 3, website: 'https://x.com' });
  const established = scoreLead({ trade: 'roofing', rating: 4.5, reviewCount: 200, website: 'https://x.com' });
  assert.ok(established.score > suspicious.score);
  assert.ok(suspicious.reasons.some(x => /near-perfect rating on few reviews/.test(x)));
});

test('poor ratings are flagged as the wrong problem to solve', () => {
  const r = scoreLead({ ...base, trade: 'roofing', rating: 2.5 });
  assert.ok(r.reasons.some(x => /follow-up will not fix reputation/.test(x)));
});

test('score never exceeds 100 and reasons are always present', () => {
  const r = scoreLead({ trade: 'remodeling', rating: 4.5, reviewCount: 100000, website: 'https://x.com' });
  assert.ok(r.score <= 100);
  assert.ok(Array.isArray(r.reasons));
});

test('an unknown trade with no ticket is rejected rather than scored blindly', () => {
  const r = scoreLead({ ...base, trade: 'underwater-basket-weaving' });
  assert.equal(r.fit, false);
});
