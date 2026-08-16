import { TRADES, MIN_TICKET } from './trades.mjs';

/**
 * Score a business 0–100 on how likely it is to buy AND to get value.
 *
 * The signals are proxies for one question: does this company generate enough
 * estimates, at a high enough value, to have a backlog worth recovering?
 *
 *   ticket   (0–40)  the trade's typical job value — the dominant factor, because
 *                    it decides whether the fee can ever pay back
 *   volume   (0–30)  review count as a stand-in for job volume
 *   systems  (0–15)  a website suggests they run software, so estimates are exportable
 *   health   (0–15)  rating band — busy and competent, but not so polished they're enterprise
 *
 * Returns { score, fit, reasons[] }. `fit:false` means do not call, and `reasons`
 * says why so the judgement is auditable rather than a bare number.
 */
export function scoreLead(lead) {
  const trade = TRADES[lead.trade];
  const reasons = [];
  let score = 0;

  // --- ticket (0-40) ---
  const ticket = lead.avgTicket ?? trade?.avgTicket ?? 0;
  if (ticket >= 10000)     { score += 40; reasons.push('high job value'); }
  else if (ticket >= 6000) { score += 32; reasons.push('good job value'); }
  else if (ticket >= 4000) { score += 24; }
  else if (ticket >= MIN_TICKET) { score += 14; reasons.push('modest job value'); }
  else {
    return {
      score: 0,
      fit: false,
      reasons: [`average job ~$${ticket.toLocaleString('en-US')} is below the $${MIN_TICKET.toLocaleString('en-US')} floor — recovery cannot cover the fee`],
    };
  }

  // --- volume (0-30) ---
  const reviews = lead.reviewCount ?? 0;
  if (reviews >= 150)     { score += 30; reasons.push('high job volume'); }
  else if (reviews >= 60) { score += 24; reasons.push('steady volume'); }
  else if (reviews >= 25) { score += 16; }
  else if (reviews >= 10) { score += 8; reasons.push('low volume — verify before calling'); }
  else { reasons.push('very few reviews, may be too small or too new'); }

  // --- systems (0-15) ---
  if (lead.website) { score += 15; }
  else { reasons.push('no website — estimates may not be exportable'); }

  // --- health (0-15) ---
  const r = lead.rating ?? 0;
  if (r >= 4.0 && r <= 4.8)      { score += 15; }
  else if (r > 4.8 && reviews >= 40) { score += 10; }
  else if (r > 4.8)              { score += 4; reasons.push('near-perfect rating on few reviews'); }
  else if (r >= 3.5)             { score += 7; reasons.push('mixed reviews — closing problem may not be follow-up'); }
  else if (r > 0)                { reasons.push('poor rating — follow-up will not fix reputation'); }

  return { score: Math.min(100, score), fit: score >= 45, reasons };
}
