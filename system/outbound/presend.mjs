#!/usr/bin/env node
// The Send gate, as an executable. Exits non-zero if ANY check fails.
// compliance/PRE-SEND-CHECKLIST.md checks 1-13. Check 14 (human approval) cannot be automated
// and is not attempted here; this tool exists so that the human review is about copy, not mechanics.

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { toRecords } from '../lib/csv.mjs';

export const REQUIRED_SENDER = {
  unsubscribe: [/unsubscribe/i, /opt[- ]?out/i, /reply .{0,20}stop/i],
  privacy: [/privacy/i],
};
const PLACEHOLDERS = [/\{\{/, /\bTODO\b/, /\bXXX\b/, /lorem ipsum/i, /\[insert/i, /<name>/i];
const DECEPTIVE_SUBJECT = [/^\s*re:/i, /^\s*fwd:/i, /^\s*fw:/i];
// A performance claim must carry a source marker "[src: …]".
// Scoped to claims about OUTCOMES — ours or our clients'. An earlier version matched any
// percentage at all, which fired on the prospect's own figures ("even a 5% denial rate",
// "if your billing company takes 6%"). Those are illustrative, not performance claims, and
// blocking them taught nothing. Substantive per-claim truthfulness is enforced upstream by
// axisbridge/claims_register.json; this is the backstop for copy that never went through it.
const PERF_CLAIM = new RegExp([
  // Past tense only. "everything we recover" is offer language describing what the
  // PROSPECT keeps, not a claim about results we have produced — it must not be blocked.
  String.raw`\bwe (?:recovered|collected|have recovered|have collected)\b`,
  String.raw`\bwe (?:typically|usually|average|consistently) (?:recover|collect|find)\b`,
  String.raw`\bour clients? (?:recover|see|average|typically|get)\b`,
  String.raw`\bclients? (?:typically|average|usually) (?:recover|see|get)\b`,
  String.raw`\$\s?\d[\d,]*(?:\.\d+)?\s*(?:recovered|in recoveries|back|returned)\b`,
  String.raw`\b\d{1,3}(?:\.\d+)?\s?%\s*(?:of (?:our|their) )?(?:recovery|recovered|success|increase|uplift|more)\b`,
  String.raw`\b(?:results?|success rate|recovery rate) of \d`,
].join('|'), 'i');
const SOURCE_MARKER = /\[src:[^\]]+\]/i;

export function checkArtifact(a, ctx) {
  const f = [];
  const body = String(a.body ?? '');
  const subject = String(a.subject ?? '');
  const to = String(a.to ?? '').trim().toLowerCase();

  if (!to) f.push('1: no recipient');
  else if (!ctx.prospectEmails.has(to)) f.push(`1: recipient ${to} is not in data/prospects.csv`);

  const p = ctx.prospectsByEmail.get(to);
  if (p) {
    if (!p.source_url) f.push(`2: prospect ${to} has no source_url`);
    if (!p.retrieved_at || Number.isNaN(Date.parse(p.retrieved_at))) f.push(`2: prospect ${to} has no parseable retrieved_at`);
    if (!p.pecr_class) f.push(`11: prospect ${to} has no pecr_class`);
    else if (p.pecr_class !== 'corporate_subscriber') f.push(`11: prospect ${to} is "${p.pecr_class}" — PECR requires consent; not sendable`);
    if (!p.source_dataset_lia_ok) { /* resolved below via LIA presence */ }
  }

  if (ctx.suppressed.has(to)) f.push(`3: recipient ${to} is on the suppression list`);
  if (!REQUIRED_SENDER.unsubscribe.some(r => r.test(body))) f.push('4: no unsubscribe instruction in body');
  if (!ctx.senderName || !body.includes(ctx.senderName)) f.push('5: sender name not present in body');
  if (!ctx.senderEntity || !body.includes(ctx.senderEntity)) f.push('5: sender legal entity not present in body');
  if (!ctx.postalAddress || !body.includes(ctx.postalAddress)) f.push('6: no physical postal address in body (CAN-SPAM)');
  if (!REQUIRED_SENDER.privacy.some(r => r.test(body))) f.push('7: no privacy notice reference in body');
  if (!subject) f.push('8: empty subject');
  if (DECEPTIVE_SUBJECT.some(r => r.test(subject))) f.push(`8: deceptive subject prefix in "${subject}"`);
  for (const r of PLACEHOLDERS) if (r.test(body) || r.test(subject)) f.push(`10: placeholder text matching ${r} left in artifact`);
  if (PERF_CLAIM.test(body) && !SOURCE_MARKER.test(body)) f.push('9: performance claim present with no [src: …] marker');
  return f;
}

export function runPresend({ outboxDir, prospectsPath, suppressionPath, liaDir, sender, volumeCap = 500 }) {
  const problems = [], notes = [];

  const prospects = existsSync(prospectsPath) ? toRecords(readFileSync(prospectsPath, 'utf8')).records : [];
  const prospectsByEmail = new Map();
  for (const p of prospects) if (p.contact_email) prospectsByEmail.set(p.contact_email.trim().toLowerCase(), p);
  const suppressed = new Set(
    (existsSync(suppressionPath) ? toRecords(readFileSync(suppressionPath, 'utf8')).records : [])
      .map(r => String(r.identifier ?? '').trim().toLowerCase()).filter(Boolean));

  const artifacts = existsSync(outboxDir)
    ? readdirSync(outboxDir).filter(f => f.endsWith('.json'))
        .map(f => { try { return { file: f, ...JSON.parse(readFileSync(join(outboxDir, f), 'utf8')) }; }
                    catch (e) { problems.push(`${f}: not valid JSON — ${e.message}`); return null; } })
        .filter(Boolean)
    : [];

  const ctx = { prospectEmails: new Set(prospectsByEmail.keys()), prospectsByEmail, suppressed, ...sender };
  for (const a of artifacts) for (const p of checkArtifact(a, ctx)) problems.push(`${a.file} — check ${p}`);

  // 12: an LIA must exist for every dataset a sendable prospect came from
  const datasets = new Set(prospects.map(p => p.source_dataset).filter(Boolean));
  for (const d of datasets) {
    const path = join(liaDir, `lia-${d}.md`);
    if (!existsSync(path)) problems.push(`12: no LIA at ${path} for dataset "${d}"`);
  }
  if (!datasets.size && prospects.length) problems.push('12: prospects present but none declare a source_dataset');

  if (artifacts.length > volumeCap) problems.push(`13: ${artifacts.length} artifacts exceeds volume cap of ${volumeCap}`);

  if (!artifacts.length) notes.push('Outbox is empty — nothing to send. This is a pass in the trivial sense only.');
  if (!prospects.length) notes.push('data/prospects.csv holds zero real records. Nothing can be sent until it holds real, sourced rows.');

  return { ok: problems.length === 0, artifacts: artifacts.length, prospects: prospects.length,
           suppressed: suppressed.size, problems, notes };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const arg = (n, d) => { const i = process.argv.indexOf(n); return i > -1 ? process.argv[i + 1] : d; };
  const r = runPresend({
    outboxDir: arg('--outbox', 'outbox'),
    prospectsPath: arg('--prospects', 'data/prospects.csv'),
    suppressionPath: arg('--suppression', 'compliance/suppression.csv'),
    liaDir: arg('--lia', 'compliance'),
    sender: { senderName: process.env.SENDER_NAME, senderEntity: process.env.SENDER_ENTITY, postalAddress: process.env.SENDER_POSTAL_ADDRESS },
  });
  console.log(`PRE-SEND: ${r.artifacts} artifact(s), ${r.prospects} prospect(s), ${r.suppressed} suppressed`);
  for (const n of r.notes) console.log(`  note: ${n}`);
  for (const p of r.problems) console.log(`  FAIL  ${p}`);
  console.log(r.ok ? '\nChecks 1-13 PASS. Check 14 (human approval) is still outstanding — it is the gate.'
                   : `\n${r.problems.length} failure(s). Send gate stays shut.`);
  process.exit(r.ok ? 0 : 1);
}
