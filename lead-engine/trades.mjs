/**
 * Target trades and their typical job value.
 *
 * `avgTicket` drives qualification, not curiosity. The ROI calculator shows the
 * offer goes underwater when recovered revenue can't clear the fee — at a $1,000/mo
 * fee and a ~5% recovery rate, a trade needs roughly a $2,500+ average job before
 * the arithmetic works at all. Trades below MIN_TICKET are kept here only so the
 * engine can explicitly reject them rather than silently miss them.
 *
 * Figures are rough US market midpoints for scoring purposes only — never quote
 * them to a prospect. Always use the contractor's own number.
 */
export const MIN_TICKET = 2500;

export const TRADES = {
  roofing:      { avgTicket: 11000, query: 'roofing contractor' },
  remodeling:   { avgTicket: 18000, query: 'home remodeling contractor' },
  hvac:         { avgTicket:  7500, query: 'hvac contractor' },
  solar:        { avgTicket: 16000, query: 'solar installer' },
  windows:      { avgTicket:  9000, query: 'window replacement contractor' },
  foundation:   { avgTicket:  8000, query: 'foundation repair' },
  paving:       { avgTicket:  6000, query: 'paving contractor driveway' },
  pool:         { avgTicket: 14000, query: 'swimming pool builder' },
  fencing:      { avgTicket:  5000, query: 'fence contractor' },
  landscaping:  { avgTicket:  4500, query: 'landscaping contractor' },
  plumbing:     { avgTicket:  3200, query: 'plumbing contractor' },
  electrical:   { avgTicket:  3000, query: 'electrical contractor' },
  // --- below the line: engine will flag these as unfit ---
  pest:         { avgTicket:   600, query: 'pest control service' },
  handyman:     { avgTicket:   700, query: 'handyman service' },
  cleaning:     { avgTicket:   300, query: 'house cleaning service' },
};

/** Trades worth building a list for. */
export const FIT_TRADES = Object.entries(TRADES)
  .filter(([, t]) => t.avgTicket >= MIN_TICKET)
  .map(([name]) => name);
