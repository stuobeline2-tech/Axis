// Ingest a de-identified claims/denial export.
// Refuses identifier columns rather than trusting the sender (shariah/c01.md §7, DECISIONS 15:06Z).

import { toRecords } from '../lib/csv.mjs';

// Matched against a normalised header (lowercased, non-alphanumerics stripped) after an optional
// subject prefix (patient/member/subscriber/...) has been stripped. The prefix strip matters:
// a column literally called "Patient Address" must be refused, not squeaked past a `^address$`.
export const SUBJECT_PREFIX = /^(patient|member|subscriber|insured|guarantor|client|responsibleparty|home|mailing|billing|primary)+/;

export const FORBIDDEN_HEADER_PATTERNS = [
  { re: /^(first|last|middle|full|given|family)?name$/,                       label: 'patient or member name' },
  { re: /^(dob|dateofbirth|birthdate|birthday)$/,                             label: 'date of birth' },
  { re: /^(ssn|socialsecurity|socialsecuritynumber|taxid)$/,                  label: 'social security number' },
  { re: /^(mrn|medicalrecordnumber|medicalrecordno|chartnumber|chartno|id|identifier|account|accountnumber|accountno)$/, label: 'medical record / patient identifier' },
  { re: /^(memberid|memberno|subscriberid|policynumber|policyno|insuranceid|hicn|mbi|certificatenumber)$/,               label: 'member or policy identifier' },
  { re: /^(address|address1|address2|addressline1|addressline2|street|streetaddress|city|state|zip|zipcode|postcode|postalcode)$/, label: 'address detail' },
  { re: /^(phone|phonenumber|telephone|mobile|cell|cellphone|fax|email|emailaddress)$/, label: 'contact detail' },
];

/** True if the header identifies a person once any subject prefix is removed. */
export function forbiddenReason(header) {
  const n = header.toLowerCase().replace(/[^a-z0-9]/g, '');
  const candidates = new Set([n]);
  let stripped = n.replace(SUBJECT_PREFIX, '');
  if (stripped && stripped !== n) candidates.add(stripped);
  for (const c of candidates) {
    for (const f of FORBIDDEN_HEADER_PATTERNS) if (f.re.test(c)) return f.label;
  }
  return null;
}

export const REQUIRED = {
  date_of_service: [/^(dateofservice|dos|servicedate|fromdate|servicefromdate)$/],
  procedure_code:  [/^(cpt|cptcode|hcpcs|procedurecode|proccode|code)$/],
  payer:           [/^(payer|payorname|payername|payor|insurance|insurancecompany|plan)$/],
  denial_code:     [/^(denialcode|carc|carccode|adjustmentreasoncode|reasoncode|denial)$/],
  billed_amount:   [/^(billedamount|charged|chargeamount|charges|billed|totalcharge)$/],
};
export const OPTIONAL = {
  allowed_amount: [/^(allowedamount|allowed)$/],
  paid_amount:    [/^(paidamount|paid|payment|paymentamount)$/],
  claim_status:   [/^(claimstatus|status)$/],
  last_action_date:[/^(lastactiondate|lastaction|remitdate|remittancedate|adjudicationdate|eobdate)$/],
  claim_ref:      [/^(claimref|claimnumber|claimid|internalclaimid)$/],
  remark_code:    [/^(remarkcode|rarc|rarccode)$/],
};

export const norm = h => h.toLowerCase().replace(/[^a-z0-9]/g, '');

export class IngestRefusal extends Error {
  constructor(message, details) { super(message); this.name = 'IngestRefusal'; this.details = details; }
}

function mapHeaders(headers) {
  const found = {}, used = new Set();
  for (const [field, pats] of Object.entries({ ...REQUIRED, ...OPTIONAL })) {
    for (const h of headers) {
      if (used.has(h)) continue;
      if (pats.some(p => p.test(norm(h)))) { found[field] = h; used.add(h); break; }
    }
  }
  return found;
}

function money(v) {
  if (v === undefined || v === null) return null;
  const s = String(v).replace(/[$£,\s]/g, '');
  if (s === '' || s === '-') return null;
  const neg = /^\(.*\)$/.test(s);
  const n = Number(neg ? s.slice(1, -1) : s);
  return Number.isFinite(n) ? (neg ? -n : n) : null;
}

function isoDate(v) {
  if (!v) return null;
  const s = String(v).trim();
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = s.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$/);   // US M/D/Y
  if (m) {
    const yr = m[3].length === 2 ? Number(m[3]) + 2000 : Number(m[3]);
    return `${yr}-${String(m[1]).padStart(2, '0')}-${String(m[2]).padStart(2, '0')}`;
  }
  return null;
}

/** Normalise a CARC to its bare code: "CO-197", "co197", "PR 1" -> "197", "1". */
export function normaliseDenialCode(raw) {
  if (!raw) return null;
  const s = String(raw).toUpperCase().trim();
  const m = s.match(/^(?:CO|PR|OA|PI)?[\s\-_]*([A-Z]?\d{1,3})$/);
  return m ? m[1] : s || null;
}

export function ingest(csvText) {
  const { headers, records } = toRecords(csvText);
  if (!headers.length) throw new IngestRefusal('The file is empty — no header row found.', {});

  // 1. PHI refusal comes FIRST, before anything is parsed or retained.
  const violations = [];
  for (const h of headers) {
    const label = forbiddenReason(h);
    if (label) violations.push({ column: h, identifies: label });
  }
  if (violations.length) {
    throw new IngestRefusal(
      `Refused: the export contains ${violations.length} identifier column(s). ` +
      `This service accepts de-identified claim-level data only. Remove these columns and re-export: ` +
      violations.map(v => `"${v.column}" (${v.identifies})`).join(', '),
      { violations });
  }

  // 2. Required columns
  const map = mapHeaders(headers);
  const missing = Object.keys(REQUIRED).filter(f => !map[f]);
  if (missing.length) {
    throw new IngestRefusal(
      `Refused: required column(s) not found: ${missing.join(', ')}. Headers seen: ${headers.join(', ')}`,
      { missing, headers });
  }

  const claims = [], rejected = [];
  records.forEach((r, i) => {
    const c = {
      row: i + 2,
      claim_ref: map.claim_ref ? r[map.claim_ref] : `row-${i + 2}`,
      date_of_service: isoDate(r[map.date_of_service]),
      procedure_code: r[map.procedure_code] || null,
      payer: r[map.payer] || null,
      denial_code: normaliseDenialCode(r[map.denial_code]),
      remark_code: map.remark_code ? (r[map.remark_code] || null) : null,
      billed_amount: money(r[map.billed_amount]),
      allowed_amount: map.allowed_amount ? money(r[map.allowed_amount]) : null,
      paid_amount: map.paid_amount ? money(r[map.paid_amount]) : null,
      claim_status: map.claim_status ? (r[map.claim_status] || null) : null,
      last_action_date: map.last_action_date ? isoDate(r[map.last_action_date]) : null,
    };
    const why = [];
    if (!c.date_of_service) why.push('unparseable date_of_service');
    if (c.billed_amount === null) why.push('unparseable billed_amount');
    if (!c.denial_code) why.push('missing denial_code');
    if (why.length) rejected.push({ row: c.row, reasons: why }); else claims.push(c);
  });

  return { claims, rejected, columns_mapped: map, columns_seen: headers };
}
