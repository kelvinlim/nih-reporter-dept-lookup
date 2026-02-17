# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python data pipeline that retrieves NIH grant data for University of Minnesota, organizes it by Principal Investigator (PI), and enriches it with PI details (rank, department, school). Two parallel implementations exist: **LDAP** (recommended, UMN-specific) and **ORCID** (institution-independent).

## Setup & Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env_sample .env  # Configure LDAP credentials

# LDAP pipeline (recommended) — run steps in order
python main_ldap.py --projects --years 10   # Step 1: Fetch NIH grants
python main_ldap.py --reorganize             # Step 2: Group by PI/Core Grant
python main_ldap.py --lookup                 # Step 3: Enrich via LDAP
python main_ldap.py --refine                 # Step 4: Map LDAP depts → official UMN school/dept/division
python main_ldap.py --refine --verbose       # Step 4: (with per-PI mapping output)
python main_ldap.py --join                   # Step 5: Produce final JSON/CSV

# ORCID pipeline — same steps, different enrichment source
python main.py --projects --years 10
python main.py --reorganize
python main.py --lookup
python main.py --join

# Structure generation
python build_schools_structure.py    # UMN org hierarchy (no PI data)
python build_nested_structure.py     # Hierarchical structure with PIs

# Verification (5 sample records)
python verify_pipeline.py
```

No test framework or linter is configured.

## Architecture

**5-step ETL pipeline (LDAP version):**

```
NIH RePORTER API → projects_raw.json → projects_by_pi.json → pi_details_*.json → (refine) → final_department_data_*.json/csv
```

1. **Extract** (`fetch_grants.py`): Paginated NIH API calls, 500/page, 1s delay
2. **Transform** (`main*.py:step_reorganize`): Groups projects by PI → Core Grant Number
3. **Enrich** (`fetch_pi_details_ldap.py` or `fetch_pi_details.py`): Lookup PI rank/department
4. **Refine** (`main_ldap.py:step_refine`): Map LDAP dept strings → official school/dept/division via `umn_structure.py`
5. **Load** (`main*.py:step_join`): Merge + flatten to JSON and CSV via pandas

**Key modules:**
- `main_ldap.py` / `main.py` — Pipeline orchestrators (argparse CLI, 5/4 step functions respectively)
- `fetch_grants.py` — NIH RePORTER v2 API client
- `fetch_pi_details_ldap.py` — LDAP lookup (single connection pooling, anonymous bind fallback, wildcard name matching to handle credentials in `sn` field)
- `fetch_pi_details.py` — ORCID Public API v3.0 client (0.5s rate limit)
- `umn_structure.py` — UMN org hierarchy definition + pattern-based department mapping (100+ patterns)
- `build_nested_structure.py` — Builds University→School→Dept→PI hierarchy from LDAP data
- `build_schools_structure.py` — Generates UMN structure without PI data

## Important Patterns

- **NIH project number parsing**: `extract_core_project_num()` strips leading application type code and suffix (e.g., `1U01DK127367-01` → `U01DK127367`)
- **LDAP connection reuse**: A single connection is created in `step_lookup()` and passed to all `get_pi_details()` calls
- **PI details caching**: Results saved to JSON every 10 records for resumability
- **Department mapping**: `umn_structure.py:get_school_for_department()` returns a 3-tuple `(school, department, division)` using case-insensitive substring matching; division is `None` for departments without divisions; unmapped departments go to "Other Departments"
- **Division support**: `UMN_STRUCTURE` uses dicts-of-lists format where each department maps to a list of divisions (empty list = no divisions). Currently only Department of Medicine has 11 divisions populated
- **LDAP name matching**: `get_pi_details()` uses 3 progressively looser LDAP filters (`sn+givenName`, `sn*+givenName`, `sn*+initial`), all requiring both first and last name. Wildcards on `sn` handle credentials in the surname field (e.g., "Bellin MD"). A post-filter verification checks the first initial of the matched entry's `givenName` to prevent wrong-person matches
- **LDAP credentials**: Read from `.env` via `python-dotenv`; never commit `.env`

## External APIs

- **NIH RePORTER v2**: `https://api.reporter.nih.gov/v2/projects/search` (public, no auth)
- **ORCID Public API v3.0**: `https://pub.orcid.org/v3.0` (public, no auth)
- **UMN LDAP**: `ldap://ldap.umn.edu:389` (requires credentials or anonymous bind, UMN network/VPN)

## Tech Stack

Python 3.10+ with `ldap3`, `requests`, `python-dotenv`, `pandas`, `beautifulsoup4`
