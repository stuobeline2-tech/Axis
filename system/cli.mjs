#!/usr/bin/env node
// Denial Recovery pipeline. One command, end to end.
//   node system/cli.mjs audit  --in <claims.csv> --practice "Name" [--out DIR] [--as-of YYYY-MM-DD]
//   node system/cli.mjs sprint --in <claims.csv> --practice "Name" [--out DIR]
//   node system/cli.mjs funnel

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { ingest, IngestRefusal } from './ingest/ingest.mjs';
import { classify, summarise, sellDecision } from './score/appealability.mjs';
import { renderAudit } from './generate/audit.mjs';
import { renderPacket } from './fulfil/packet.mjs';
import { computeFunnel, renderFunnel } from './dashboard/funnel.mjs';

const argv = process.argv.slice(2);
const cmd = argv[0];
const arg = (n, d) => { const i = argv.indexOf(n); return i > -1 ? argv[i + 1] : d; };
const asOf = arg('--as-of', new Date().toISOString().slice(0, 10));
const preparedBy = process.env.SENDER_NAME || process.env.USER || 'the operator';

function loadAndScore() {
  const inPath = arg('--in');
  if (!inPath) { console.error('--in <claims.csv> is required'); process.exit(2); }
  let report;
  try { report = ingest(readFileSync(inPath, 'utf8')); }
  catch (e) {
    if (e instanceof IngestRefusal) { console.error(`\nINGEST REFUSED\n${e.message}\n`); process.exit(3); }
    throw e;
  }
  const classified = classify(report.claims, { asOf });
  const summary = summarise(classified);
  return { report, classified, summary, decision: sellDecision(summary) };
}

if (cmd === 'audit') {
  const practice = arg('--practice', 'the practice');
  const outDir = arg('--out', 'out');
  const { report, summary, decision } = loadAndScore();
  mkdirSync(outDir, { recursive: true });
  const md = renderAudit({ practice, summary, decision, ingestReport: report, asOf, preparedBy });
  const path = join(outDir, `audit-${practice.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${asOf}.md`);
  writeFileSync(path, md);
  console.log(`Audit written: ${path}`);
  console.log(`  claims analysed          ${summary.total_claims}`);
  console.log(`  total denied outstanding $${summary.total_denied_outstanding.toLocaleString()}`);
  console.log(`  confirmed appealable     $${summary.confirmed_appealable_dollars.toLocaleString()}`);
  console.log(`  window unknown           $${summary.unknown_window_dollars.toLocaleString()}`);
  console.log(`  expired (lost)           $${summary.expired_dollars.toLocaleString()}`);
  console.log(`\n  SELL DECISION: ${decision.may_sell ? 'MAY OFFER SPRINT' : 'DO NOT SELL'}`);
  console.log(`  ${decision.reason}`);
} else if (cmd === 'sprint') {
  const practice = arg('--practice', 'the practice');
  const outDir = arg('--out', 'out/packets');
  const { summary, decision } = loadAndScore();
  if (!decision.may_sell) {
    console.error(`\nREFUSED: ${decision.reason}\nThe Sprint is not sellable to this practice. Deliver the free audit instead.\n`);
    process.exit(4);
  }
  mkdirSync(outDir, { recursive: true });
  let n = 0;
  for (const c of summary.worklist) {
    writeFileSync(join(outDir, `packet-${String(++n).padStart(3, '0')}-${String(c.claim_ref).replace(/[^a-zA-Z0-9]+/g, '-')}.md`),
                  renderPacket(c, { practice, preparedBy, asOf }));
  }
  console.log(`${n} appeal packet(s) written to ${outDir}`);
} else if (cmd === 'funnel') {
  console.log(renderFunnel(computeFunnel(readFileSync(arg('--ledger', 'metrics/ledger.csv'), 'utf8'))));
} else {
  console.log(`usage:
  node system/cli.mjs audit  --in <claims.csv> --practice "Name" [--out DIR] [--as-of YYYY-MM-DD]
  node system/cli.mjs sprint --in <claims.csv> --practice "Name" [--out DIR]
  node system/cli.mjs funnel [--ledger metrics/ledger.csv]`);
  process.exit(cmd ? 2 : 0);
}
