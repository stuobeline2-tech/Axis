# Session capability constraint (recorded 2026-08-16T14:54Z)

Verified by direct test, not assumed:

| Capability | Result |
|---|---|
| `WebSearch` (server-side, Anthropic) | **WORKS** — returns real titles, URLs, snippets |
| `WebFetch` on any third-party host | **BLOCKED** — `EGRESS_BLOCKED` |
| `curl` to any non-allowlisted host | **BLOCKED** — gateway 403 to CONNECT |
| `github.com` / `api.github.com` | WORKS (http 200) |
| package registries (npm, pypi, crates, go) | in `noProxy`, reachable |
| `npiregistry.cms.hhs.gov` (NPPES API) | **BLOCKED** (403 CONNECT) |
| `download.cms.gov` (NPPES bulk files) | **BLOCKED** |
| `reddit.com`, `upwork.com`, `remotive.com`, `remoteok.com` | **BLOCKED** |
| `contractsfinder.service.gov.uk` | **BLOCKED** |
| `en.wikipedia.org`, `cms.gov`, `news.ycombinator.com` | **BLOCKED** |

Proxy evidence: `curl "$HTTPS_PROXY/__agentproxy/status"` → `recentRelayFailures` lists each
host with `"gateway answered 403 to CONNECT (policy denial or upstream failure)"`.

## Consequences for this spec, stated up front

1. **Evidence grade.** Every Phase-1 evidence item is a *search-result record* — a real URL and
   a real snippet returned by a live query this session. The page body was NOT fetched. Every
   evidence file states this. No evidence item is presented as a verified page read.
2. **Phase 5 prospect data.** Building `data/prospects.csv` requires retrieving and verifying
   individual businesses and contacts. With no fetch capability and no NPPES access, that cannot
   be done on real data in this session. Under §2.1 the correct outcome is `BLOCKED`, not a
   plausible-looking CSV. Two unblock paths exist and are documented in `STATE.md`.
3. **Phase 4 test input.** A "real input" per the acceptance criterion must come from the
   operator or a reachable source. Where a fixture is used instead, it lives under `test/` and
   is labelled a fixture — never under `data/`.
