#!/usr/bin/env node
// Draft personalised outreach artifacts into outbox/. Drafts only — sending is the §1.1 Send gate.
//
// Refuses to invent. Every message must cite a specific observation drawn from the prospect row
// itself; a row with no observation produces NO artifact rather than a generic one. Every
// statistic carries an inline [src: …] marker, which the pre-send gate then enforces.

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { toRecords } from '../lib/csv.mjs';

export const SOURCED_STATS = {
  denial_rate: { text: 'initial denial rates now average about 11.8% industry-wide', src: 'qualigenix.com/claim-denials-2026' },
  never_reworked: { text: 'roughly 60% of denied claims are never reworked at all', src: 'ircm.com/blog/medical-practice-revenue-leakage' },
  rework_cost: { text: 'MGMA puts the cost of reworking a single denied claim at $25–$181', src: 'ircm.com/blog/medical-practice-revenue-leakage' },
};

export function buildMessage(p, sender, stat = SOURCED_STATS.never_reworked) {
  if (!p.observation) return null;           // no specific observation -> no message. Not negotiable.
  const name = p.contact_name?.trim() || 'there';
  const subject = `Denied claims at ${p.org_name}`;
  const body =
`Hi ${name},

${p.observation}

Practices your size usually have a stack of denials nobody has time to rework — ${stat.text} [src: ${stat.src}]. Some of them still have an open appeal window; the rest have quietly passed their filing deadline and are gone for good.

I can tell you which is which. I run a free audit on a de-identified claims export — no patient names, no dates of birth, no member IDs — and send back the total that is still appealable, ranked by value, in two business days. If it turns out there isn't much there, I'll say so and that's the end of it.

Worth a look?

${sender.senderName}
${sender.senderEntity}
${sender.postalAddress}
Privacy notice: ${sender.privacyUrl}

Don't want these? Reply STOP and I'll remove you permanently — no reply needed beyond that word.`;
  return { to: p.contact_email, prospect_id: p.npi || p.contact_email, org_name: p.org_name,
           subject, body, drafted_at: new Date().toISOString(), status: 'AWAITING_SEND_GATE' };
}

export function generate({ prospectsPath, outboxDir, sender }) {
  const prospects = existsSync(prospectsPath) ? toRecords(readFileSync(prospectsPath, 'utf8')).records : [];
  mkdirSync(outboxDir, { recursive: true });
  let written = 0, skipped = [];
  for (const p of prospects) {
    if (!p.contact_email) { skipped.push(`${p.org_name || 'row'}: no contact_email`); continue; }
    if (p.pecr_class !== 'corporate_subscriber') { skipped.push(`${p.org_name}: pecr_class="${p.pecr_class}" — consent required, not drafted`); continue; }
    const m = buildMessage(p, sender);
    if (!m) { skipped.push(`${p.org_name}: no specific observation — refusing to draft a generic message`); continue; }
    writeFileSync(join(outboxDir, `${(p.npi || p.contact_email).replace(/[^a-zA-Z0-9]+/g, '-')}.json`), JSON.stringify(m, null, 2));
    written++;
  }
  return { written, skipped, prospects: prospects.length };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const need = ['SENDER_NAME', 'SENDER_ENTITY', 'SENDER_POSTAL_ADDRESS', 'SENDER_PRIVACY_URL'].filter(k => !process.env[k]);
  if (need.length) { console.error(`Missing required env: ${need.join(', ')}\nThese appear verbatim in every message; there is no default and no placeholder.`); process.exit(2); }
  const r = generate({ prospectsPath: 'data/prospects.csv', outboxDir: 'outbox',
    sender: { senderName: process.env.SENDER_NAME, senderEntity: process.env.SENDER_ENTITY,
              postalAddress: process.env.SENDER_POSTAL_ADDRESS, privacyUrl: process.env.SENDER_PRIVACY_URL } });
  console.log(`${r.prospects} prospect(s) read → ${r.written} artifact(s) drafted into outbox/`);
  for (const s of r.skipped) console.log(`  skipped ${s}`);
  if (!r.prospects) console.log('\ndata/prospects.csv is empty. Nothing drafted, because there is nothing real to draft from.');
}
