"""Static configuration. Nothing here is invented at runtime."""
from __future__ import annotations

STATES = {"TX": "Texas", "FL": "Florida", "GA": "Georgia"}

# Phase 2 variable table, verbatim from the brief.
PAYERS = {
    "TX": ["Blue Cross Blue Shield of Texas", "Superior HealthPlan", "Aetna Better Health"],
    "FL": ["Florida Blue", "Sunshine Health", "Simply Healthcare"],
    "GA": ["Anthem BCBS Georgia", "Peach State Health Plan", "CareSource"],
}

DENIAL_REASON_BY_CREDENTIAL = {
    "LCSW": "90837 downcoded to 90834",
    "LPC":  "90837 downcoded to 90834",
    "LMFT": "90837 downcoded to 90834",
    "MD":    "prior auth lapses on medication management",
    "PMHNP": "prior auth lapses on medication management",
    "PsyD":  "testing codes 96130-96139 denied on units billed",
}

CREDENTIALS = tuple(DENIAL_REASON_BY_CREDENTIAL)

# --- ICP exclusions (brief: "wrong ICP, do not source or send to these") -------------
# Matched case-insensitively against the NPPES organisation name AND the clustered
# practice name. Deliberately broad: a false exclude costs one lead, a false include
# puts a publicly-funded agency into a cold sequence built for private practices.
EXCLUSION_PATTERNS = [
    r"\blmha\b", r"\blocal mental health authority\b",
    r"\bcsb\b", r"\bcommunity service board\b",
    r"\bdbhdd\b", r"\bdepartment of behavioral health\b",
    r"\bmanaging entity\b",
    r"\bnami\b", r"\bnational alliance on mental illness\b",
    r"\bcommunity mental health\b", r"\bcmhc\b",
    r"\bcounty\b", r"\bcity of\b", r"\bstate of\b",
    r"\bdepartment of (health|state health)\b", r"\bhealth district\b",
    r"\bpublic health\b", r"\bschool district\b", r"\bisd\b",
    r"\buniversity\b", r"\bcollege\b",
    r"\bveterans affairs\b", r"\bva medical\b",
    r"\bhospital\b", r"\bhealth system\b", r"\bmedical center\b",
    r"\bfederally qualified\b", r"\bfqhc\b",
    r"\bcorrectional\b", r"\bjail\b", r"\bprison\b",
]

# NPPES organisation taxonomies that signal a facility/agency rather than a private
# practice. Excluded regardless of name.
EXCLUDED_TAXONOMY_CODES = {
    "261QM0801X",  # Clinic/Center, Mental Health (incl. Community Mental Health Center)
    "261QM0850X",  # Clinic/Center, Adult Mental Health
    "261QM0855X",  # Clinic/Center, Adolescent and Children Mental Health
    "283Q00000X",  # Psychiatric Hospital
    "320800000X",  # Community Based Residential Treatment, Mental Illness
    "323P00000X",  # Psychiatric Residential Treatment Facility
    "324500000X",  # Substance Abuse Rehabilitation Facility
    "251S00000X",  # Community/Behavioral Health agency
    "261QF0400X",  # Clinic/Center, Federally Qualified Health Center
}

MAX_CLINICIANS = 10          # "solo to 10 clinicians"
MIN_ENUMERATION_MONTHS = 9   # youngest band starts at 9 months

# --- CAN-SPAM footer ------------------------------------------------------------------
# Appended to EVERY email. FOOTER_ADDRESS has no default on purpose: a placeholder
# postal address in a CAN-SPAM footer is worse than none, because it looks compliant.
FOOTER_ADDRESS_ENV = "AXISBRIDGE_POSTAL_ADDRESS"
FOOTER_OPTOUT = "Reply STOP to opt out."

# The brief specifies a two-line footer (address + opt-out) for CAN-SPAM. That covers the
# US recipient. It does NOT cover the UK controller: Axisbridge is UK-registered, so UK
# GDPR applies to this processing wherever the data subject sits, and Art. 14 requires
# privacy information be given to people whose data was obtained from a third-party
# source — which NPPES is. compliance/lia-nppes.md §6 already commits to "a link in every
# message to a published privacy notice".
# Set AXISBRIDGE_PRIVACY_URL to add the line. Left unset, the pre-send gate fails check 7
# and the batch does not go out — the decision surfaces rather than being silently skipped.
FOOTER_PRIVACY_ENV = "AXISBRIDGE_PRIVACY_URL"

SIGNATURE_FIRST = "Anthony\nAxisbridge Medical Staffing"   # step 1 of every sequence
SIGNATURE_FOLLOWUP = "Anthony"                              # in-thread follow-ups

# Names that must never appear in outbound copy (brief: Abdikarim is introduced only
# after an audit is delivered).
FORBIDDEN_IN_OUTREACH = ["Abdikarim"]

# Price points that must never appear in outreach or in an automated reply.
FORBIDDEN_PRICE_TOKENS = [
    "$2,400", "$1,900", "$7,200", "$1,500", "$93,900", "$2400", "$1900", "$7200",
    "30-Day Collections Recovery", "Denial Recovery Sprint", "Empty Chair Guarantee",
    "per month for a dedicated", "4th month free",
]

# Removed deliberately — must never reappear anywhere in the pipeline.
BANNED_OFFERS = ["2-week trial", "two week trial", "free trial", "% off", "discount"]
