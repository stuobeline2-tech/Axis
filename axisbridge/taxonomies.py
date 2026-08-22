"""
NUCC behavioural-health taxonomy codes for the FL/TX/GA NPPES pull.

    ############################################################################
    #  THIS IS NOT THE OPERATOR'S COMPILED 71-CODE SET.                        #
    #                                                                          #
    #  The brief refers to "the same 71-taxonomy-code, six-category            #
    #  behavioral-health set already compiled for the FL/TX/GA pull". That set #
    #  lives on the Axisbridge VPS and is not in this repository. It was not   #
    #  retrievable in the session that wrote this file.                        #
    #                                                                          #
    #  What follows is a RECONSTRUCTION from the NUCC taxonomy standard,       #
    #  organised into the six categories the brief names. It is SHORT of 71.   #
    #  Codes carry a confidence flag. Nothing was padded to reach 71 — an      #
    #  invented taxonomy code silently returns zero rows and you would never   #
    #  know a category was missing.                                            #
    #                                                                          #
    #  BEFORE THE PRODUCTION PULL: replace CODES with the compiled set, or run #
    #      python -m axisbridge.lead_engine --validate-taxonomies              #
    #  which queries NPPES once per code and reports every code returning zero #
    #  results, so a wrong code is visible in one command instead of silently  #
    #  shrinking the funnel.                                                   #
    ############################################################################
"""
from __future__ import annotations
from dataclasses import dataclass

HIGH, MED = "high", "medium"

@dataclass(frozen=True)
class Taxonomy:
    code: str
    label: str
    category: str
    credential: str          # maps to {{credential}} / {{denial_reason}}
    confidence: str

C_PSYCH   = "Psychiatry & Mental Health"
C_CLINPSY = "Clinical Psychology"
C_MHC     = "Mental Health Counseling"
C_ADDX    = "Addiction Medicine"
C_CSW     = "Clinical Social Work"
C_MFT     = "Marriage & Family Therapy"

CATEGORIES = (C_PSYCH, C_CLINPSY, C_MHC, C_ADDX, C_CSW, C_MFT)

CODES: tuple[Taxonomy, ...] = (
    # --- Psychiatry & Mental Health -------------------------------------------------
    Taxonomy("2084P0800X", "Psychiatry",                                   C_PSYCH, "MD",    HIGH),
    Taxonomy("2084P0804X", "Child & Adolescent Psychiatry",                C_PSYCH, "MD",    HIGH),
    Taxonomy("2084P0805X", "Geriatric Psychiatry",                         C_PSYCH, "MD",    HIGH),
    Taxonomy("2084P0015X", "Psychosomatic Medicine",                       C_PSYCH, "MD",    MED),
    Taxonomy("2084F0202X", "Forensic Psychiatry",                          C_PSYCH, "MD",    MED),
    Taxonomy("2084B0040X", "Behavioral Neurology & Neuropsychiatry",       C_PSYCH, "MD",    MED),
    Taxonomy("363LP0808X", "Nurse Practitioner, Psychiatric/Mental Health", C_PSYCH, "PMHNP", HIGH),
    Taxonomy("364SP0808X", "Clinical Nurse Specialist, Psych/Mental Health", C_PSYCH, "PMHNP", HIGH),
    Taxonomy("364SP0809X", "Clinical Nurse Specialist, Psych/MH, Adult",    C_PSYCH, "PMHNP", MED),
    Taxonomy("364SP0807X", "Clinical Nurse Specialist, Psych/MH, Child & Adolescent", C_PSYCH, "PMHNP", MED),
    Taxonomy("163WP0808X", "Registered Nurse, Psychiatric/Mental Health",   C_PSYCH, "PMHNP", MED),

    # --- Clinical Psychology --------------------------------------------------------
    Taxonomy("103T00000X", "Psychologist",                                 C_CLINPSY, "PsyD", HIGH),
    Taxonomy("103TC0700X", "Psychologist, Clinical",                       C_CLINPSY, "PsyD", HIGH),
    Taxonomy("103TC2200X", "Psychologist, Clinical Child & Adolescent",    C_CLINPSY, "PsyD", HIGH),
    Taxonomy("103TB0200X", "Psychologist, Cognitive & Behavioral",         C_CLINPSY, "PsyD", HIGH),
    Taxonomy("103TC1900X", "Psychologist, Counseling",                     C_CLINPSY, "PsyD", HIGH),
    Taxonomy("103TF0000X", "Psychologist, Family",                         C_CLINPSY, "PsyD", MED),
    Taxonomy("103TH0004X", "Psychologist, Health",                         C_CLINPSY, "PsyD", MED),
    Taxonomy("103TP2701X", "Psychologist, Group Psychotherapy",            C_CLINPSY, "PsyD", MED),
    Taxonomy("103TP0814X", "Psychologist, Psychoanalysis",                 C_CLINPSY, "PsyD", MED),
    Taxonomy("103TP0016X", "Psychologist, Prescribing (Medical)",          C_CLINPSY, "PsyD", MED),
    Taxonomy("103TA0400X", "Psychologist, Addiction",                      C_CLINPSY, "PsyD", MED),
    Taxonomy("103TA0700X", "Psychologist, Adult Development & Aging",      C_CLINPSY, "PsyD", MED),
    Taxonomy("103TR0400X", "Psychologist, Rehabilitation",                 C_CLINPSY, "PsyD", MED),
    Taxonomy("103TW0100X", "Psychologist, Women",                          C_CLINPSY, "PsyD", MED),
    Taxonomy("103G00000X", "Clinical Neuropsychologist",                   C_CLINPSY, "PsyD", HIGH),
    Taxonomy("103GC0700X", "Clinical Neuropsychologist, Clinical",         C_CLINPSY, "PsyD", MED),

    # --- Mental Health Counseling ---------------------------------------------------
    Taxonomy("101Y00000X", "Counselor",                                    C_MHC, "LPC", HIGH),
    Taxonomy("101YM0800X", "Counselor, Mental Health",                     C_MHC, "LPC", HIGH),
    Taxonomy("101YP2500X", "Counselor, Professional",                      C_MHC, "LPC", HIGH),
    Taxonomy("101YP1600X", "Counselor, Pastoral",                          C_MHC, "LPC", MED),
    Taxonomy("251500000X", "Behavioral Health Counselor (organisation)",   C_MHC, "LPC", MED),

    # --- Addiction Medicine ---------------------------------------------------------
    Taxonomy("2084A0401X", "Addiction Medicine (Psychiatry & Neurology)",  C_ADDX, "MD",  HIGH),
    Taxonomy("2084P0802X", "Addiction Psychiatry",                         C_ADDX, "MD",  HIGH),
    Taxonomy("207QA0401X", "Family Medicine, Addiction Medicine",          C_ADDX, "MD",  MED),
    Taxonomy("101YA0400X", "Counselor, Addiction (Substance Use Disorder)", C_ADDX, "LPC", HIGH),

    # --- Clinical Social Work -------------------------------------------------------
    Taxonomy("104100000X", "Social Worker",                                C_CSW, "LCSW", HIGH),
    Taxonomy("1041C0700X", "Social Worker, Clinical",                      C_CSW, "LCSW", HIGH),

    # --- Marriage & Family Therapy --------------------------------------------------
    Taxonomy("106H00000X", "Marriage & Family Therapist",                  C_MFT, "LMFT", HIGH),
)

EXPECTED_COUNT = 71
BY_CODE = {t.code: t for t in CODES}

def by_category(cat: str) -> tuple[Taxonomy, ...]:
    return tuple(t for t in CODES if t.category == cat)

def credential_for(code: str, default: str = "LPC") -> str:
    t = BY_CODE.get(code)
    return t.credential if t else default

def shortfall_warning() -> str | None:
    """Returned (and logged loudly) whenever the set is not the compiled 71."""
    if len(CODES) == EXPECTED_COUNT:
        return None
    return (
        f"TAXONOMY SET IS A RECONSTRUCTION: {len(CODES)} codes loaded, brief specifies "
        f"{EXPECTED_COUNT}. {EXPECTED_COUNT - len(CODES)} codes from the operator's compiled "
        f"set are missing, so this pull WILL under-source. Replace axisbridge/taxonomies.py "
        f"CODES with the compiled set, or run --validate-taxonomies against NPPES first."
    )
