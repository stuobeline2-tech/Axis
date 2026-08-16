// Classify denied claims and decide whether we are allowed to sell the Sprint.
// The 5x rule (offer/offer.md Guarantee 1) is enforced here, in code.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const load = p => JSON.parse(readFileSync(fileURLToPath(new URL(p, import.meta.url)), 'utf8'));

export const SPRINT_PRICE_USD = 1500;
export const MIN_MULTIPLE = 5;                       // will not sell below 5x the fee
export const SPRINT_CLAIM_CAP = 40;

/** Recoverable value of a denied claim = what was billed and not paid. */
export function outstanding(claim) {
  if (claim.billed_amount === null) return 0;
  const paid = claim.paid_amount ?? 0;
  return Math.max(0, claim.billed_amount - paid);
}

function daysBetween(aIso, bIso) {
  return Math.floor((Date.parse(bIso) - Date.parse(aIso)) / 86_400_000);
}

/**
 * Window status is one of:
 *   'open'            - inside the payer's documented appeal window
 *   'expired'         - outside it; the money is gone, and we say so
 *   'window_unknown'  - the payer has no documented window in config. NEVER assumed either way.
 */
export function windowStatus(claim, windows, asOf) {
  const cfg = windows.payers?.[claim.payer];
  const days = cfg?.appeal_window_days ?? windows.default_days;
  if (days === null || days === undefined) return { status: 'window_unknown', days: null, days_left: null, source: null };
  const from = claim.last_action_date || claim.date_of_service;
  const elapsed = daysBetween(from, asOf);
  const left = days - elapsed;
  return { status: left >= 0 ? 'open' : 'expired', days, days_left: left, source: cfg?.source ?? null,
           counted_from: claim.last_action_date ? 'last_action_date' : 'date_of_service' };
}

export function classify(claims, { asOf = new Date().toISOString().slice(0, 10), codes = load('../config/denial-codes.json'), windows = load('../config/payer-windows.json') } = {}) {
  return claims.map(c => {
    const def = codes.codes[c.denial_code] || null;
    const w = windowStatus(c, windows, asOf);
    const value = outstanding(c);
    let disposition;
    if (!def)                       disposition = 'unknown_code';
    else if (!def.appealable)       disposition = 'not_appealable';
    else if (w.status === 'expired') disposition = 'expired';
    else if (w.status === 'window_unknown') disposition = 'appealable_window_unknown';
    else                            disposition = 'appealable';
    return {
      ...c, outstanding: value,
      code_meaning: def?.meaning ?? null,
      category: def?.category ?? 'unknown',
      action: def?.action ?? 'manual_review',
      window: w, disposition,
    };
  });
}

export function summarise(classified) {
  const bucket = k => classified.filter(c => c.disposition === k);
  const sum = arr => Math.round(arr.reduce((t, c) => t + c.outstanding, 0) * 100) / 100;

  const appealable = bucket('appealable');
  const unknownWindow = bucket('appealable_window_unknown');
  const expired = bucket('expired');
  const notAppealable = bucket('not_appealable');
  const unknownCode = bucket('unknown_code');

  const byCode = {};
  for (const c of classified) {
    const k = c.denial_code ?? 'none';
    byCode[k] ??= { code: k, meaning: c.code_meaning, category: c.category, count: 0, dollars: 0 };
    byCode[k].count++; byCode[k].dollars += c.outstanding;
  }
  const topCodes = Object.values(byCode)
    .map(x => ({ ...x, dollars: Math.round(x.dollars * 100) / 100 }))
    .sort((a, b) => b.dollars - a.dollars);

  // Deliberately CONSERVATIVE: the confirmed-recoverable figure the sell decision uses
  // counts only claims whose window we can actually evidence as open.
  const confirmed = sum(appealable);

  return {
    total_claims: classified.length,
    total_denied_outstanding: sum(classified),
    confirmed_appealable_dollars: confirmed,
    unknown_window_dollars: sum(unknownWindow),
    expired_dollars: sum(expired),
    not_appealable_dollars: sum(notAppealable),
    unknown_code_dollars: sum(unknownCode),
    counts: { appealable: appealable.length, window_unknown: unknownWindow.length,
              expired: expired.length, not_appealable: notAppealable.length, unknown_code: unknownCode.length },
    top_codes: topCodes,
    worklist: [...appealable, ...unknownWindow].sort((a, b) => b.outstanding - a.outstanding).slice(0, SPRINT_CLAIM_CAP),
  };
}

/**
 * Guarantee 1, in code: we do not sell the Sprint unless CONFIRMED appealable dollars
 * clear 5x the fee. Claims with an unknown filing window do not count towards the threshold —
 * counting them would let a config gap manufacture a sale.
 */
export function sellDecision(summary, { price = SPRINT_PRICE_USD, multiple = MIN_MULTIPLE } = {}) {
  const threshold = price * multiple;
  const may = summary.confirmed_appealable_dollars >= threshold;
  return {
    may_sell: may, threshold, price, multiple,
    confirmed: summary.confirmed_appealable_dollars,
    reason: may
      ? `Confirmed appealable $${summary.confirmed_appealable_dollars.toLocaleString()} clears the $${threshold.toLocaleString()} threshold.`
      : `Confirmed appealable $${summary.confirmed_appealable_dollars.toLocaleString()} is below the $${threshold.toLocaleString()} threshold (${multiple}x the $${price.toLocaleString()} fee). DO NOT SELL THE SPRINT. Deliver the audit and say so plainly.`
      + (summary.unknown_window_dollars > 0
          ? ` Note: $${summary.unknown_window_dollars.toLocaleString()} sits in claims whose payer appeal window is not documented in config — that is a gap to close, not a reason to sell.`
          : ''),
  };
}
