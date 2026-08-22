"""
PHASE 1 — lead sourcing and enrichment.

    python -m axisbridge.lead_engine --states TX FL GA --out data/leads_database.json
    python -m axisbridge.lead_engine --validate-taxonomies
    python -m axisbridge.lead_engine --verify-emails-only data/leads_database.json

NETWORK NOTE: NPPES and practice-website HTTP are blocked by egress policy in some
environments (they were in the session that wrote this). MX verification works
everywhere DNS works. Run this on the Axisbridge VPS, not in a restricted sandbox.
"""
from __future__ import annotations
import argparse, asyncio, json, logging, pathlib, re, sys, urllib.parse
from collections import defaultdict
from datetime import date, datetime

from . import config, taxonomies, routing

log = logging.getLogger("lead_engine")

NPPES = "https://npiregistry.cms.hhs.gov/api/"
NPPES_LIMIT = 200          # API maximum
NPPES_SKIP_CEILING = 1000  # API maximum; (skip+limit) cannot exceed 1200

# NPPES 2.1 has no taxonomy-CODE parameter — only taxonomy_description. So we query
# broadly by description and filter precisely by code client-side. That way a wrong
# description costs recall we can measure, not silent precision loss.
QUERY_DESCRIPTIONS = [
    "Psychiatry", "Psychiatry & Neurology", "Psychologist", "Clinical Neuropsychologist",
    "Counselor", "Social Worker", "Marriage & Family Therapist",
    "Nurse Practitioner", "Clinical Nurse Specialist", "Addiction Medicine",
]

WANTED_CODES = set(taxonomies.BY_CODE)
EXCLUDE_RE = re.compile("|".join(config.EXCLUSION_PATTERNS), re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
GENERIC_LOCALPARTS = ("info", "admin", "office", "contact", "billing", "hello", "reception", "frontdesk")
JUNK_EMAIL = re.compile(r"(example|sentry|wixpress|godaddy|squarespace|\.png|\.jpg|@2x|no-?reply|donotreply)", re.I)


# --------------------------------------------------------------------------- NPPES
async def _nppes_page(session, state: str, desc: str, skip: int) -> list[dict]:
    params = {"version": "2.1", "state": state, "taxonomy_description": desc,
              "limit": NPPES_LIMIT, "skip": skip}
    async with session.get(NPPES, params=params, timeout=30) as r:
        r.raise_for_status()
        data = await r.json()
    if "Errors" in data:
        log.warning("NPPES error for %s/%s: %s", state, desc, data["Errors"])
        return []
    return data.get("results", []) or []


async def fetch_state(session, state: str) -> list[dict]:
    out, saturated = [], []
    for desc in QUERY_DESCRIPTIONS:
        skip = 0
        while skip <= NPPES_SKIP_CEILING:
            page = await _nppes_page(session, state, desc, skip)
            if not page:
                break
            out.extend(page)
            if len(page) < NPPES_LIMIT:
                break
            skip += NPPES_LIMIT
            await asyncio.sleep(0.35)          # rate limit, unconditional
        else:
            saturated.append(desc)
    if saturated:
        log.warning(
            "QUERY SATURATED for %s on: %s. NPPES caps results at skip+limit=1200, so these "
            "queries returned a TRUNCATED slice of the real population. Re-run sliced by city "
            "or postal prefix (--postal-prefixes) before treating this pull as complete.",
            state, ", ".join(saturated))
    return out


# ------------------------------------------------------------------- normalisation
def _addr(rec: dict) -> dict | None:
    for a in rec.get("addresses", []):
        if a.get("address_purpose") == "LOCATION":
            return a
    return None


def _months_since(iso: str | None) -> int | None:
    if not iso:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            d = datetime.strptime(iso[:10], fmt).date()
            break
        except ValueError:
            continue
    else:
        return None
    t = date.today()
    return (t.year - d.year) * 12 + (t.month - d.month)


def _practice_name(rec: dict, addr: dict) -> str:
    b = rec.get("basic", {})
    return (b.get("organization_name") or b.get("name")
            or f"{b.get('first_name','')} {b.get('last_name','')}".strip()
            or addr.get("address_1", "unknown"))


def _address_key(addr: dict) -> str:
    line = re.sub(r"[^a-z0-9]", "", (addr.get("address_1") or "").lower())
    return f"{line}|{(addr.get('city') or '').lower()}|{(addr.get('state') or '').upper()}|{(addr.get('postal_code') or '')[:5]}"


def _matching_taxonomy(rec: dict):
    for t in rec.get("taxonomies", []):
        code = t.get("code")
        if code in config.EXCLUDED_TAXONOMY_CODES:
            return "EXCLUDED"
        if code in WANTED_CODES:
            return taxonomies.BY_CODE[code]
    return None


def cluster(records: list[dict]) -> list[dict]:
    """One practice = one lead, keyed on location address. Counts co-located NPIs."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    excluded = {"taxonomy": 0, "name": 0, "no_address": 0, "no_taxonomy_match": 0}

    for rec in records:
        addr = _addr(rec)
        if not addr:
            excluded["no_address"] += 1
            continue
        tax = _matching_taxonomy(rec)
        if tax == "EXCLUDED":
            excluded["taxonomy"] += 1
            continue
        if tax is None:
            excluded["no_taxonomy_match"] += 1
            continue
        name = _practice_name(rec, addr)
        org = (rec.get("basic", {}).get("organization_name") or "")
        if EXCLUDE_RE.search(name) or EXCLUDE_RE.search(org):
            excluded["name"] += 1
            continue
        buckets[_address_key(addr)].append({"rec": rec, "addr": addr, "tax": tax, "name": name})

    leads = []
    for key, members in buckets.items():
        if len(members) > config.MAX_CLINICIANS:
            continue                                    # "solo to 10 clinicians"
        addr = members[0]["addr"]
        state = (addr.get("state") or "").upper()
        if state not in config.STATES:
            continue
        # Practice name: prefer an organisation name if any co-located NPI has one.
        org_names = [m for m in members if m["rec"].get("basic", {}).get("organization_name")]
        primary = org_names[0] if org_names else members[0]
        enum_months = min((_months_since(m["rec"].get("basic", {}).get("enumeration_date"))
                           for m in members if _months_since(m["rec"].get("basic", {}).get("enumeration_date")) is not None),
                          default=None)
        entity = "org" if any(m["rec"].get("enumeration_type") == "NPI-2" for m in members) else "individual"
        credential = primary["tax"].credential
        leads.append({
            "lead_id": key,
            "practice_name": primary["name"],
            "npis": [m["rec"].get("number") for m in members],
            "clinician_count": len(members),
            "entity_type": "org" if (entity == "org" or len(members) > 1) else "individual",
            "address_1": addr.get("address_1"), "city": (addr.get("city") or "").title(),
            "state_code": state, "state": config.STATES[state],
            "postal_code": (addr.get("postal_code") or "")[:5],
            "phone": addr.get("telephone_number"),
            "taxonomy_code": primary["tax"].code, "taxonomy_label": primary["tax"].label,
            "category": primary["tax"].category, "credential": credential,
            "enumeration_months": enum_months,
            "enumeration_band": routing.enumeration_band(enum_months),
            "denial_reason": config.DENIAL_REASON_BY_CREDENTIAL.get(credential),
            "payer": config.PAYERS[state][0],
            "source_url": f"{NPPES}?version=2.1&number={members[0]['rec'].get('number')}",
            "retrieved_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "source_dataset": "nppes",
            "website": None, "contact_email": None, "first_name": None,
            "email_verified": False, "email_verification": None,
        })
    log.info("clustered %d records -> %d practices (excluded: %s)", len(records), len(leads), excluded)
    return leads


# ------------------------------------------------------------------- website crawl
async def _robots_allows(session, base: str, path: str = "/contact") -> bool:
    """Fail CLOSED: if robots.txt cannot be read or disallows, we do not crawl."""
    try:
        async with session.get(urllib.parse.urljoin(base, "/robots.txt"), timeout=12) as r:
            if r.status != 200:
                return True                     # no robots.txt published = no restriction
            body = (await r.text())[:20000]
    except Exception:
        return False
    agent_all, disallowed = False, []
    for line in body.splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            agent_all = v == "*"
        elif k == "disallow" and agent_all and v:
            disallowed.append(v)
    return not any(path.startswith(d) for d in disallowed)


async def find_email(session, lead: dict, sem: asyncio.Semaphore) -> None:
    site = lead.get("website")
    if not site:
        return
    base = site if site.startswith("http") else f"https://{site}"
    async with sem:
        if not await _robots_allows(session, base):
            lead["email_verification"] = "robots.txt disallows"
            return
        for path in ("/contact", "/contact-us", "/about", "/"):
            try:
                async with session.get(urllib.parse.urljoin(base, path), timeout=15) as r:
                    if r.status != 200:
                        continue
                    html = (await r.text(errors="ignore"))[:400_000]
            except Exception:
                continue
            found = [e for e in EMAIL_RE.findall(html) if not JUNK_EMAIL.search(e)]
            if found:
                found.sort(key=lambda e: (0 if e.split("@")[0].lower().startswith(GENERIC_LOCALPARTS) else 1, len(e)))
                lead["contact_email"] = found[0].lower()
                lead["email_source_url"] = urllib.parse.urljoin(base, path)
                return
            await asyncio.sleep(1.0)          # rate limit between page fetches


# --------------------------------------------------------------------- MX verify
def verify_email(addr: str | None) -> tuple[bool, str]:
    """Syntax + DNS MX. Verified working in a restricted sandbox where HTTP was blocked."""
    if not addr:
        return False, "no address"
    if not re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", addr):
        return False, "syntax"
    domain = addr.rsplit("@", 1)[1].lower()
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX", lifetime=8)
        if not answers:
            return False, "no MX records"
        return True, f"MX ok ({str(answers[0].exchange).rstrip('.')})"
    except ImportError:
        return False, "dnspython not installed"
    except Exception as e:
        return False, f"MX lookup failed: {type(e).__name__}"


def verify_all(leads: list[dict]) -> dict[str, int]:
    stats = defaultdict(int)
    for lead in leads:
        ok, why = verify_email(lead.get("contact_email"))
        lead["email_verified"], lead["email_verification"] = ok, why
        stats["verified" if ok else "dropped"] += 1
    return dict(stats)


def finalise(leads: list[dict]) -> list[dict]:
    """Drop unverified (brief step 6), assign exactly one sequence (step 7)."""
    kept = [l for l in leads if l.get("email_verified")]
    for l in kept:
        seq, why = routing.assign_sequence(l)
        l["sequence"], l["sequence_reason"] = seq, why
        l["pecr_class"] = "corporate_subscriber" if l["entity_type"] == "org" else "individual"
    return kept


# ------------------------------------------------------------------------- main
async def run(states: list[str], out: pathlib.Path, crawl: bool) -> None:
    import aiohttp
    if (w := taxonomies.shortfall_warning()):
        log.warning(w)
    async with aiohttp.ClientSession(headers={"User-Agent": "AxisbridgeLeadEngine/1.0 (+https://www.axisbridgemedical.com)"}) as s:
        records = []
        for st in states:
            got = await fetch_state(s, st)
            log.info("%s: %d NPPES records", st, len(got))
            records.extend(got)
        leads = cluster(records)
        if crawl:
            sem = asyncio.Semaphore(5)
            await asyncio.gather(*(find_email(s, l, sem) for l in leads))
    log.info("MX verification: %s", verify_all(leads))
    final = finalise(leads)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(final, indent=2) + "\n")
    log.info("wrote %d sendable leads to %s (from %d clustered practices)", len(final), out, len(leads))


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--states", nargs="+", default=["TX", "FL", "GA"])
    p.add_argument("--out", type=pathlib.Path, default=pathlib.Path("data/leads_database.json"))
    p.add_argument("--no-crawl", action="store_true", help="skip website crawling (MX-only run)")
    p.add_argument("--validate-taxonomies", action="store_true")
    p.add_argument("--verify-emails-only", type=pathlib.Path)
    a = p.parse_args(argv)

    if a.validate_taxonomies:
        return _validate_taxonomies()
    if a.verify_emails_only:
        leads = json.loads(a.verify_emails_only.read_text())
        print(verify_all(leads))
        a.verify_emails_only.write_text(json.dumps(leads, indent=2) + "\n")
        return 0
    asyncio.run(run(a.states, a.out, crawl=not a.no_crawl))
    return 0


def _validate_taxonomies() -> int:
    """Query NPPES once per code and report every code that returns nothing."""
    import aiohttp

    async def go():
        dead = []
        async with aiohttp.ClientSession() as s:
            for t in taxonomies.CODES:
                try:
                    async with s.get(NPPES, params={"version": "2.1", "state": "TX",
                                                    "taxonomy_description": t.label, "limit": 1}, timeout=25) as r:
                        d = await r.json()
                    n = d.get("result_count", 0)
                except Exception as e:
                    print(f"  ERROR {t.code} {t.label}: {type(e).__name__}")
                    dead.append(t)
                    continue
                flag = "" if n else "   <-- ZERO RESULTS"
                print(f"  {t.code}  {t.confidence:<6} {t.label[:48]:<48} {n}{flag}")
                if not n:
                    dead.append(t)
                await asyncio.sleep(0.35)
        print(f"\n{len(dead)} of {len(taxonomies.CODES)} codes returned nothing — verify these against NUCC.")
        if (w := taxonomies.shortfall_warning()):
            print("\n" + w)
        return 0
    return asyncio.run(go())


if __name__ == "__main__":
    sys.exit(main())
