#!/usr/bin/env node
// Pipeline CRM. Deliberately small: its only job is to make the real conversion
// rates visible early, so a broken script gets caught in a week, not a quarter.
import { open, moveStage, funnel, STAGES } from '../lib/db.mjs';

const db = open();
const [cmd, ...args] = process.argv.slice(2);

const bold = s => `\x1b[1m${s}\x1b[0m`;
const dim  = s => `\x1b[2m${s}\x1b[0m`;
const pct  = (a, b) => (b > 0 ? ((a / b) * 100).toFixed(1) + '%' : '—');

/** Parse `--key value` and `--key=value` pairs off an argv slice. */
function flags(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) continue;
    const eq = a.indexOf('=');
    if (eq > -1) out[a.slice(2, eq)] = a.slice(eq + 1);
    else if (argv[i + 1] && !argv[i + 1].startsWith('--')) out[a.slice(2)] = argv[++i];
    else out[a.slice(2)] = true;
  }
  return out;
}

const commands = {
  add() {
    const f = flags(args);
    if (!f.business) return fail('add requires --business "Name"');
    const { lastInsertRowid } = db.prepare(`
      INSERT INTO leads (business, trade, metro, phone, website, owner_name, avg_ticket, source)
      VALUES (?,?,?,?,?,?,?,?)
    `).run(
      f.business, f.trade ?? null, f.metro ?? null, f.phone ?? null,
      f.website ?? null, f.owner ?? null, f.ticket ? Number(f.ticket) : null,
      f.source ?? 'manual',
    );
    console.log(`Added #${lastInsertRowid} ${bold(f.business)}`);
  },

  move() {
    const [id, stage] = args;
    if (!id || !stage) return fail('move <id> <stage> [--reason "..."]');
    const lead = moveStage(db, Number(id), stage, flags(args).reason ?? null);
    console.log(`#${lead.id} ${bold(lead.business)} → ${bold(lead.stage)}`);
  },

  touch() {
    const [id, channel] = args;
    if (!id || !channel) return fail('touch <id> <call|email|voicemail|sms|meeting> [--outcome x] [--note "..."]');
    const f = flags(args);
    db.prepare('INSERT INTO touches (lead_id, channel, outcome, note) VALUES (?,?,?,?)')
      .run(Number(id), channel, f.outcome ?? null, f.note ?? null);
    // First real contact attempt should advance the lead out of `queued` on its own.
    const lead = db.prepare('SELECT stage FROM leads WHERE id = ?').get(Number(id));
    if (lead?.stage === 'queued') moveStage(db, Number(id), 'contacted', 'first touch logged');
    console.log(`Logged ${channel} on #${id}`);
  },

  list() {
    const f = flags(args);
    const where = [], params = [];
    if (f.stage) { where.push('stage = ?'); params.push(f.stage); }
    if (f.metro) { where.push('metro = ?'); params.push(f.metro); }
    const rows = db.prepare(`
      SELECT id, business, trade, metro, phone, score, stage FROM leads
      ${where.length ? 'WHERE ' + where.join(' AND ') : ''}
      ORDER BY score DESC, id ASC LIMIT ?
    `).all(...params, Number(f.limit ?? 30));

    if (!rows.length) return console.log(dim('No leads match.'));
    console.log(bold('  ID  SCORE  STAGE          TRADE       BUSINESS'));
    for (const r of rows) {
      console.log(
        String(r.id).padStart(4),
        String(r.score ?? 0).padStart(6),
        '  ' + (r.stage ?? '').padEnd(14),
        (r.trade ?? '—').padEnd(11),
        r.business + (r.phone ? dim('  ' + r.phone) : ''),
      );
    }
  },

  /** The call list: highest-scoring leads that haven't been contacted yet. */
  next() {
    const n = Number(flags(args).n ?? 20);
    const rows = db.prepare(`
      SELECT id, business, trade, metro, phone, score FROM leads
      WHERE stage = 'queued' ORDER BY score DESC, id ASC LIMIT ?
    `).all(n);
    if (!rows.length) return console.log(dim('Queue is empty — run `npm run leads` to build the list.'));
    console.log(bold(`Next ${rows.length} to call:\n`));
    for (const r of rows) {
      console.log(`  #${String(r.id).padEnd(5)} ${bold((r.business ?? '').padEnd(34))} ${(r.phone ?? 'no phone').padEnd(16)} ${dim(`${r.trade ?? '?'} · ${r.metro ?? '?'} · score ${r.score}`)}`);
    }
    console.log(dim('\n  Log outcomes:  npm run pipeline -- touch <id> call --outcome spoke'));
  },

  funnel() {
    const { byStage, reached, disqualified, total } = funnel(db);
    if (!total) return console.log(dim('No leads yet.'));

    console.log(bold('\nFunnel\n'));
    console.log(dim('  STAGE            REACHED   NOW   CONV FROM PREV'));
    let prev = null;
    for (const stage of STAGES) {
      const r = reached[stage], now = byStage[stage] ?? 0;
      console.log(
        '  ' + stage.padEnd(15),
        String(r).padStart(6),
        String(now).padStart(6),
        '   ' + (prev === null ? dim('—') : pct(r, prev)),
      );
      prev = r;
    }
    if (disqualified) console.log('  ' + dim('disqualified'.padEnd(15) + String(disqualified).padStart(6)));

    const retained = reached.retained ?? 0;
    const contacted = reached.contacted ?? 0;
    console.log(bold('\nWhat this tells you\n'));
    console.log(`  Contacted → retained : ${pct(retained, contacted)}`);
    console.log(`  MRR at $1,000/client : $${((byStage.retained ?? 0) * 1000).toLocaleString('en-US')}/mo`);
    console.log(`  Daily equivalent     : $${Math.round((byStage.retained ?? 0) * 1000 * 12 / 365)}/day`);
    const gap = 8 - (byStage.retained ?? 0);
    console.log(gap > 0
      ? dim(`  ${gap} more retained clients to reach $250/day.\n`)
      : bold('  Target reached.\n'));
  },

  show() {
    const id = Number(args[0]);
    if (!id) return fail('show <id>');
    const lead = db.prepare('SELECT * FROM leads WHERE id = ?').get(id);
    if (!lead) return fail(`No lead #${id}`);
    console.log(bold(`\n#${lead.id} ${lead.business}`));
    for (const k of ['trade', 'metro', 'phone', 'website', 'owner_name', 'avg_ticket', 'score', 'stage']) {
      if (lead[k] != null) console.log(`  ${k.padEnd(12)} ${lead[k]}`);
    }
    const touches = db.prepare('SELECT * FROM touches WHERE lead_id = ? ORDER BY occurred_at').all(id);
    if (touches.length) {
      console.log(bold('\n  Touches'));
      for (const t of touches) {
        console.log(`    ${t.occurred_at}  ${t.channel.padEnd(9)} ${(t.outcome ?? '').padEnd(14)} ${t.note ?? ''}`);
      }
    }
    console.log('');
  },

  help() {
    console.log(`
${bold('Axis pipeline')}

  npm run pipeline -- add --business "Ace Roofing" --trade roofing --metro "Dallas TX" --phone 214... --ticket 9000
  npm run pipeline -- next [--n 20]              highest-scoring uncontacted leads
  npm run pipeline -- touch <id> call --outcome spoke --note "..."
  npm run pipeline -- move <id> <stage> --reason "..."
  npm run pipeline -- list [--stage demo] [--metro "Dallas TX"] [--limit 30]
  npm run pipeline -- show <id>
  npm run funnel                                 conversion rates + distance to target

  ${dim('stages: ' + STAGES.join(' → ') + '  (+ disqualified)')}
`);
  },
};

function fail(msg) {
  console.error(`error: ${msg}`);
  process.exitCode = 1;
}

(commands[cmd] ?? commands.help)();
