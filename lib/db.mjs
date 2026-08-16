// Shared SQLite layer. Uses Node's built-in node:sqlite — no dependencies, no native build.
import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

export const DB_PATH = process.env.AXIS_DB ?? resolve(process.cwd(), 'data/axis.db');

/**
 * Pipeline stages, in order. A lead moves left to right; `disqualified` is a
 * terminal side-exit that can happen from anywhere and is deliberately NOT part
 * of the funnel sequence, so it never pollutes conversion rates.
 */
export const STAGES = [
  'queued',        // on the list, never contacted
  'contacted',     // outreach attempted, no reply yet
  'conversation',  // a human actually replied / picked up
  'demo',          // walked them through the ROI calculator
  'pilot_sold',    // paid for the one-off pilot
  'retained',      // on the monthly retainer — this is the one that pays rent
  'churned',
];

export const TERMINAL = new Set(['churned', 'disqualified']);

const SCHEMA = `
CREATE TABLE IF NOT EXISTS leads (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  business      TEXT NOT NULL,
  trade         TEXT,
  metro         TEXT,
  phone         TEXT,
  website       TEXT,
  owner_name    TEXT,
  rating        REAL,
  review_count  INTEGER,
  avg_ticket    INTEGER,           -- estimated, used for fit scoring
  score         INTEGER DEFAULT 0,
  stage         TEXT NOT NULL DEFAULT 'queued',
  source        TEXT,
  place_id      TEXT UNIQUE,       -- dedupe key from Google Places
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS touches (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id     INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  channel     TEXT NOT NULL,       -- call | email | voicemail | sms | meeting
  outcome     TEXT,                -- no_answer | gatekeeper | spoke | booked | not_interested
  note        TEXT,
  occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stage_history (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id    INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  from_stage TEXT,
  to_stage   TEXT NOT NULL,
  reason     TEXT,
  changed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_leads_stage  ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_score  ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_touches_lead ON touches(lead_id);
`;

export function open(path = DB_PATH) {
  mkdirSync(dirname(path), { recursive: true });
  const db = new DatabaseSync(path);
  db.exec('PRAGMA journal_mode = WAL;');
  db.exec('PRAGMA foreign_keys = ON;');
  db.exec(SCHEMA);
  return db;
}

/** Move a lead to a new stage and record why. Returns the updated row. */
export function moveStage(db, leadId, toStage, reason = null) {
  if (!STAGES.includes(toStage) && toStage !== 'disqualified') {
    throw new Error(`Unknown stage "${toStage}". Valid: ${[...STAGES, 'disqualified'].join(', ')}`);
  }
  const lead = db.prepare('SELECT * FROM leads WHERE id = ?').get(leadId);
  if (!lead) throw new Error(`No lead with id ${leadId}`);

  db.prepare('UPDATE leads SET stage = ?, updated_at = datetime(\'now\') WHERE id = ?')
    .run(toStage, leadId);
  db.prepare('INSERT INTO stage_history (lead_id, from_stage, to_stage, reason) VALUES (?,?,?,?)')
    .run(leadId, lead.stage, toStage, reason);

  return db.prepare('SELECT * FROM leads WHERE id = ?').get(leadId);
}

/**
 * Funnel counts. A lead that has reached a later stage is counted as having
 * passed every earlier one — otherwise a lead sitting in `retained` would read
 * as though it never had a conversation, and the rates would be nonsense.
 */
export function funnel(db) {
  const rows = db.prepare('SELECT stage, COUNT(*) AS n FROM leads GROUP BY stage').all();
  const byStage = Object.fromEntries(rows.map(r => [r.stage, r.n]));

  const reached = {};
  STAGES.forEach((stage, i) => {
    reached[stage] = STAGES.slice(i)
      .reduce((sum, later) => sum + (byStage[later] ?? 0), 0);
  });
  return {
    byStage,
    reached,
    disqualified: byStage.disqualified ?? 0,
    total: rows.reduce((s, r) => s + r.n, 0),
  };
}
