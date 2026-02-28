# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python data pipeline that retrieves NIH grant data for University of Minnesota, organizes it by Principal Investigator (PI), and enriches it with PI details (rank, department, school). Two parallel implementations exist: **LDAP** (recommended, UMN-specific) and **ORCID** (institution-independent). A separate **VA pipeline** retrieves VA-funded grants nationally and supplements with VA website data.

## Setup & Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env_sample .env  # Configure LDAP credentials

# LDAP pipeline (recommended) — run steps in order
python3 main_ldap.py --projects --years 10   # Step 1: Fetch NIH grants
python3 main_ldap.py --reorganize             # Step 2: Group by PI/Core Grant
python3 main_ldap.py --lookup                 # Step 3: Enrich via LDAP
python3 main_ldap.py --lookup --name "Smith"  # Step 3: Re-lookup specific PI (overwrites cached)
python3 main_ldap.py --refine                 # Step 4: Map LDAP depts → official UMN school/dept/division
python3 main_ldap.py --refine --verbose       # Step 4: (with per-PI mapping output)
python3 main_ldap.py --join                   # Step 5: Produce final JSON/CSV
python3 main_ldap.py --pack                   # Step 6: Pack for Runway import

# ORCID pipeline — same steps, different enrichment source
python3 main.py --projects --years 10
python3 main.py --reorganize
python3 main.py --lookup
python3 main.py --join

# VA pipeline — no LDAP required, uses NIH API + VA website scraping
python3 main_va.py --projects --years 5                    # Step 1: Fetch VA grants
python3 main_va.py --projects --years 5 --org "MINNEAPOLIS VA MEDICAL CENTER"  # Filtered
python3 main_va.py --reorganize                            # Step 2: Group by PI
python3 main_va.py --scrape --years 5                      # Step 3: Scrape VA website (optional)
python3 main_va.py --scrape --years 5 --skip-details       # Step 3: Listing only (fast)
python3 main_va.py --join                                  # Step 4: Merge → JSON/CSV
python3 main_va.py --pack                                  # Step 5: Runway import

# Structure generation
python3 build_schools_structure.py    # UMN org hierarchy (no PI data)
python3 build_nested_structure.py     # Hierarchical structure with PIs

# Verification (5 sample records)
python3 verify_pipeline.py
```

No test framework or linter is configured.

## Architecture

**6-step ETL pipeline (LDAP version):**

```
NIH RePORTER API → projects_raw.json → projects_by_pi.json → pi_details_*.json → (refine) → final_department_data_*.json/csv → runway_import.json
```

1. **Extract** (`fetch_grants.py`): Paginated NIH API calls, 500/page, 1s delay
2. **Transform** (`main*.py:step_reorganize`): Groups projects by PI → Core Grant Number
3. **Enrich** (`fetch_pi_details_ldap.py` or `fetch_pi_details.py`): Lookup PI rank/department
4. **Refine** (`main_ldap.py:step_refine`): Map LDAP dept strings → official school/dept/division via `pi_overrides.json` (if present) then `umn_structure.py` pattern matching
5. **Load** (`main*.py:step_join`): Merge + flatten to JSON and CSV via pandas
6. **Pack** (`main_ldap.py:step_pack`): Combine units hierarchy + enriched projects into single Runway import file (`units` key = org hierarchy, `projects` key = enriched grant data)

**5-step VA pipeline:**

```
NIH RePORTER API (VA filter) → va_projects_raw.json → va_projects_by_pi.json → (scrape) → va_project_details.json → va_final_data.json/csv → va_runway_import.json
```

1. **Extract** (`fetch_va_grants.py`): NIH API with `agencies: ["VA"]`, optional `--org` filter
2. **Transform** (`main_va.py:step_reorganize`): Groups projects by PI → Core Grant Number
3. **Scrape** (`scrape_va_details.py`): Optional VA website scraping for total_award_amount, location, service
4. **Load** (`main_va.py:step_join`): Merge API + scraped data → JSON and CSV via pandas
5. **Pack** (`main_va.py:step_pack`): Runway import with Organization → Site → Unit hierarchy

**Key modules:**
- `main_ldap.py` / `main.py` — Pipeline orchestrators (argparse CLI, 6/4 step functions respectively)
- `main_va.py` — VA pipeline orchestrator (5 steps: projects → reorganize → scrape → join → pack)
- `fetch_grants.py` — NIH RePORTER v2 API client (UMN grants)
- `fetch_va_grants.py` — NIH RePORTER v2 API client (VA grants, `agencies: ["VA"]` filter)
- `scrape_va_details.py` — VA website scraper (listing pages + detail pages for total award, location, service)
- `fetch_pi_details_ldap.py` — LDAP lookup (single connection pooling, anonymous bind fallback, wildcard name matching to handle credentials in `sn` field)
- `fetch_pi_details.py` — ORCID Public API v3.0 client (0.5s rate limit)
- `umn_structure.py` — UMN org hierarchy definition + pattern-based department mapping (100+ patterns)
- `build_nested_structure.py` — Builds University→School→Dept→PI hierarchy from LDAP data
- `build_schools_structure.py` — Generates UMN structure without PI data

## Data Files

| File | Description |
|------|-------------|
| `projects_raw.json` | Raw NIH RePORTER API response |
| `projects_by_pi.json` | Projects grouped by PI → Core Grant Number |
| `pi_details_ldap.json` | LDAP lookup cache (gains `school_official`/`department_official`/`division_official` after refine) |
| `pi_details.json` | ORCID lookup cache |
| `final_department_data_ldap.json/csv` | Final merged dataset (LDAP) |
| `final_department_data.json/csv` | Final merged dataset (ORCID) |
| `umn_schools_departments.json` | UMN org hierarchy (no PI data) |
| `nested_structure.json` | Hierarchical org structure with PIs embedded |
| `pi_overrides.json` | Manual PI/department mapping overrides (survives re-runs, used by `--refine`) |
| `unmapped_none_pis.json` | Template for PIs with no LDAP record (fill in and merge into `pi_overrides.json`) |
| `runway_import.json` | Combined units + projects for Runway import |
| `va_projects_raw.json` | Raw NIH RePORTER API response (VA grants) |
| `va_projects_by_pi.json` | VA projects grouped by PI → Core Grant Number |
| `va_project_details.json` | VA website scraping cache (total award, location, service) |
| `va_final_data.json/csv` | Final merged VA dataset |
| `va_runway_import.json` | VA Runway import (hierarchy: Organization → Site → Unit) |

## Important Patterns

- **NIH project number parsing**: `extract_core_project_num()` strips leading application type code and suffix (e.g., `1U01DK127367-01` → `U01DK127367`)
- **LDAP connection reuse**: A single connection is created in `step_lookup()` and passed to all `get_pi_details()` calls
- **PI details caching**: Results saved to JSON every 10 records for resumability. Use `--name` filter with `--lookup` to re-process specific PIs (overwrites their cached entries)
- **Department mapping**: `umn_structure.py:get_school_for_department()` returns a 3-tuple `(school, department, division)` using word-boundary regex matching; division is `None` for departments without divisions; unmapped departments go to "Other Departments". To add new mappings, add keyword patterns to the `dept_patterns` dict in `get_school_for_department()`
- **PI overrides**: `pi_overrides.json` provides manual corrections applied in `step_refine()` before pattern matching. Resolution order: (1) PI-level override → (2) department-level override → (3) pattern matching → (4) unmapped. Two sections:
  - `pi_overrides`: Keyed by PI name (e.g., `"BLAZAR, BRUCE R"`), for individual corrections when LDAP dept is wrong/missing
  - `department_overrides`: Keyed by raw LDAP dept string (e.g., `"NSU Neurosurgery Dept Admin"`), for admin units that should map to a specific school/dept
  - Each entry has `school_official`, `department_official`, `division_official` (nullable), and `reason` (documentary)
  - Set `school_official` to `null` to explicitly mark as unmapped/skip
  - `unmapped_none_pis.json`: Helper file with empty templates for PIs with no LDAP record, ready to fill in and merge into `pi_overrides`
  - Verbose output shows source: `O` = PI override, `D` = dept override, `P` = pattern match, `✗` = unmapped
- **Division support**: `UMN_STRUCTURE` uses dicts-of-lists format where each department maps to a list of divisions (empty list = no divisions). Currently only Department of Medicine has 11 divisions populated. In `nested_structure.json`, divided departments become nested dicts (`{Division → [PIs]}`) while undivided departments are flat lists (`[PIs]`)
- **LDAP name matching**: `get_pi_details()` uses 4 progressively looser LDAP filters: (1) exact `sn`+`givenName`, (2) exact `sn`+`givenName*`, (3) `sn*`+`givenName*`, (4) `sn*`+`initial*`. Wildcards on `sn` handle credentials in the surname field (e.g., "Bellin MD"). A post-filter scoring system (exact givenName=2, prefix=1, initial-only=0) selects the best candidate across all filters, returning early only on exact matches
- **LDAP credentials**: Read from `.env` via `python-dotenv`; never commit `.env`
- **VA pipeline**: Uses same NIH RePORTER API with `agencies: ["VA"]` filter. No LDAP — PI emails are name-based placeholders (`firstname.lastname@va.placeholder`). VA website scraping (optional) adds `total_award_amount`, `location`, `research_service`. Scraping matches projects by core project number since API and website use different suffix formats. `--skip-details` skips detail page scraping (listing pages only). Runway hierarchy: Organization → Site (auto-discovered from `org_city, org_state`) → Unit (placeholder for future GRECC/COIN/CCDOR)
- **VA website scraping**: Two phases — (1) listing pages (`projects-FY{YEAR}.cfm`) build project_num→pid index, (2) detail pages (`proj-details-FY{YEAR}.cfm?pid={pid}`) extract total award, location, service. FY2025+ has "Location" column; earlier years have "Service" column. Caching + checkpointing every 10 records for resumability

## External APIs

- **NIH RePORTER v2**: `https://api.reporter.nih.gov/v2/projects/search` (public, no auth) — supports VA grants via `agencies: ["VA"]` filter
- **ORCID Public API v3.0**: `https://pub.orcid.org/v3.0` (public, no auth)
- **UMN LDAP**: `ldap://ldap.umn.edu:389` (requires credentials or anonymous bind, UMN network/VPN)
- **VA Research Website**: `https://www.research.va.gov/about/funded_research/` (public, scraped for supplemental data)

## Tech Stack

Python 3.10+ with `ldap3`, `requests`, `python-dotenv`, `pandas`, `beautifulsoup4`
