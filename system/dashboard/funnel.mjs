// Metrics from metrics/ledger.csv. Undefined on zero rows is reported as null, never as 0%.
import { readFileSync } from 'node:fs';
import { toRecords } from '../lib/csv.mjs';

const STAGES = ['contacted', 'replied', 'positive_reply', 'call_booked', 'proposal_sent', 'paid'];

export function computeFunnel(csvText) {
  const { records } = toRecords(csvText);
  if (!records.length) {
    return { rows: 0, note: 'No real events logged. Every metric is null because nothing has happened yet — not because it is zero.',
             stages: Object.fromEntries(STAGES.map(s => [s, 0])), conversions: Object.fromEntries(STAGES.slice(1).map(s => [s, null])),
             revenue_gbp: null, cost_gbp: null, profit_gbp: null, refund_rate: null,
             revenue_per_100_prospects: null, profit_per_100_prospects: null,
             revenue_per_human_hour: null, profit_per_human_hour: null, mean_fulfilment_hours: null };
  }
  const uniq = s => new Set(records.filter(r => r.stage === s).map(r => r.prospect_id)).size;
  const stages = Object.fromEntries(STAGES.map(s => [s, uniq(s)]));
  const num = (r, k) => { const n = Number(r[k]); return Number.isFinite(n) ? n : 0; };
  const paidRows = records.filter(r => r.stage === 'paid');
  const refundRows = records.filter(r => r.stage === 'refunded');
  const revenue = paidRows.reduce((t, r) => t + num(r, 'amount_gbp'), 0);
  const refunds = refundRows.reduce((t, r) => t + num(r, 'amount_gbp'), 0);
  const cost = records.reduce((t, r) => t + num(r, 'cost_gbp'), 0);
  const hours = records.reduce((t, r) => t + num(r, 'fulfilment_hours'), 0);
  const net = revenue - refunds;
  const profit = net - cost;
  const div = (a, b) => (b > 0 ? Math.round((a / b) * 100) / 100 : null);

  const conversions = {};
  STAGES.slice(1).forEach((s, i) => { const prev = stages[STAGES[i]]; conversions[s] = prev > 0 ? Math.round((stages[s] / prev) * 1000) / 10 : null; });

  return {
    rows: records.length, note: null, stages, conversions,
    revenue_gbp: net, cost_gbp: cost, profit_gbp: profit,
    refund_rate: paidRows.length > 0 ? Math.round((refundRows.length / paidRows.length) * 1000) / 10 : null,
    revenue_per_100_prospects: div(net * 100, stages.contacted),
    profit_per_100_prospects: div(profit * 100, stages.contacted),
    revenue_per_human_hour: div(net, hours),
    profit_per_human_hour: div(profit, hours),
    mean_fulfilment_hours: div(hours, paidRows.length),
  };
}

export function renderFunnel(f) {
  const v = x => (x === null ? 'null' : x);
  const L = ['DENIAL RECOVERY — FUNNEL', ''];
  if (f.note) L.push(f.note, '');
  L.push('Stage                 count    conv%');
  for (const [k, n] of Object.entries(f.stages)) L.push(`${k.padEnd(20)} ${String(n).padStart(5)}    ${v(f.conversions[k] ?? '—')}`);
  L.push('', `revenue £${v(f.revenue_gbp)}   cost £${v(f.cost_gbp)}   profit £${v(f.profit_gbp)}`,
         `revenue/100 prospects  ${v(f.revenue_per_100_prospects)}`,
         `profit/100 prospects   ${v(f.profit_per_100_prospects)}`,
         `revenue/human hour     ${v(f.revenue_per_human_hour)}`,
         `profit/human hour      ${v(f.profit_per_human_hour)}`,
         `refund rate %          ${v(f.refund_rate)}`);
  return L.join('\n');
}
