#!/usr/bin/env node
// Builds and scores the target list, writing straight into the pipeline as `queued`.
import { open } from '../lib/db.mjs';
import { searchPlaces } from './places.mjs';
import { scoreLead } from './score.mjs';
import { TRADES, FIT_TRADES } from './trades.mjs';

const bold = s => `\x1b[1m${s}\x1b[0m`;
const dim  = s => `\x1b[2m${s}\x1b[0m`;

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

const f = flags(process.argv.slice(2));

if (f.help || (!f.metro && !f.trades)) {
  console.log(`
${bold('Axis lead engine')}

  npm run leads -- --metro "Dallas TX" --trade roofing
  npm run leads -- --metro "Dallas TX" --trades roofing,hvac,remodeling --pages 3
  npm run leads -- --metro "Dallas TX" --trade roofing --dry-run

  ${dim('--metro    required, e.g. "Dallas TX"')}
  ${dim('--trade    single trade   --trades  comma list   (default: all fit trades)')}
  ${dim('--pages    result pages per trade, 20 each (default 3)')}
  ${dim('--dry-run  print what would be saved, write nothing')}
  ${dim('--min      minimum score to keep (default 45)')}

  ${dim('fit trades: ' + FIT_TRADES.join(', '))}
`);
  process.exit(0);
}

const metro    = f.metro;
const minScore = Number(f.min ?? 45);
const trades   = f.trade ? [f.trade]
               : f.trades ? String(f.trades).split(',').map(s => s.trim())
               : FIT_TRADES;

for (const t of trades) {
  if (!TRADES[t]) {
    console.error(`error: unknown trade "${t}". Known: ${Object.keys(TRADES).join(', ')}`);
    process.exit(1);
  }
}

const apiKey = process.env.GOOGLE_PLACES_API_KEY;
if (!apiKey && !f['dry-run']) {
  console.error('error: GOOGLE_PLACES_API_KEY not set. Use --dry-run to preview scoring without it.');
  process.exit(1);
}

const db = open();
const insert = db.prepare(`
  INSERT INTO leads (business, trade, metro, phone, website, rating, review_count, avg_ticket, score, source, place_id)
  VALUES (?,?,?,?,?,?,?,?,?,?,?)
  ON CONFLICT(place_id) DO NOTHING
`);

let found = 0, kept = 0, skipped = 0, dupes = 0;

for (const trade of trades) {
  const query = `${TRADES[trade].query} in ${metro}`;
  process.stdout.write(dim(`searching: ${query} … `));

  let places;
  try {
    places = f['dry-run']
      ? sampleFor(trade)
      : await searchPlaces({ query, apiKey, maxPages: Number(f.pages ?? 3) });
  } catch (err) {
    console.log('');
    console.error(`error on "${trade}": ${err.message}`);
    continue;
  }

  console.log(`${places.length} results`);
  found += places.length;

  for (const p of places) {
    const { score, fit, reasons } = scoreLead({ ...p, trade });

    if (!fit || score < minScore) {
      skipped++;
      if (f.verbose) console.log(dim(`  skip  ${p.business} (${score}) — ${reasons[0] ?? 'below threshold'}`));
      continue;
    }

    if (f['dry-run']) {
      kept++;
      console.log(`  ${bold(String(score).padStart(3))}  ${p.business.padEnd(32)} ${dim(reasons.join('; '))}`);
      continue;
    }

    const r = insert.run(
      p.business, trade, metro, p.phone ?? null, p.website ?? null,
      p.rating ?? null, p.reviewCount ?? 0, TRADES[trade].avgTicket, score,
      'google_places', p.placeId,
    );
    if (r.changes === 0) dupes++; else kept++;
  }
}

console.log('');
console.log(bold('Done.'));
console.log(`  found ${found}   kept ${bold(String(kept))}   below bar ${skipped}   already had ${dupes}`);

if (!f['dry-run']) {
  const q = db.prepare("SELECT COUNT(*) AS n FROM leads WHERE stage = 'queued'").get();
  console.log(`  queued to call: ${bold(String(q.n))}`);
  console.log(dim('\n  next:  npm run next'));
}

/** Fixture data so scoring can be exercised without an API key or spend. */
function sampleFor(trade) {
  return [
    { placeId: `s-${trade}-1`, business: `Summit ${trade} Co`,   phone: '214-555-0111', website: 'https://example.com', rating: 4.6, reviewCount: 210 },
    { placeId: `s-${trade}-2`, business: `Lone Star ${trade}`,   phone: '214-555-0112', website: 'https://example.com', rating: 4.3, reviewCount: 74  },
    { placeId: `s-${trade}-3`, business: `Budget ${trade}`,      phone: '214-555-0113', website: null,                 rating: 3.2, reviewCount: 9   },
    { placeId: `s-${trade}-4`, business: `Perfect ${trade} LLC`, phone: '214-555-0114', website: 'https://example.com', rating: 5.0, reviewCount: 3   },
  ];
}
