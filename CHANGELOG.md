# Changelog

## 2026-02-28

### Added
- **Shared schema module** (`schemas/`): JSON schema definitions and CPOS pre-computation utilities shared across pipelines
  - `base_person_schema.json` / `base_project_schema.json` — common fields
  - `va_person_schema.json` / `va_project_schema.json` — VA-specific extensions (total_award_amount, portfolio, research_service)
  - `umn_person_schema.json` — UMN-specific person fields (ORCID iD)
  - `schemas/__init__.py` — `load_schemas()` and `precompute_cpos()` helpers
- **CPOS pre-computation in export**: Both pipelines now pre-compute all `cpos.*` attributes in `step_pack()` instead of relying on hardcoded derivation in Runway's `import_bulk.py`
  - VA pipeline uses scraped `total_award_amount` for `cpos.award_amount` and per-site location
  - LDAP pipeline uses FY amount x estimated project years and global UMN location
- **New Runway import metadata fields**:
  - `auto_populate_cpos` (boolean, default true): When false, skips CPOS auto-derivation in import — new exports set this to false since CPOS is pre-computed
  - `cpos_defaults` (dict): Static CPOS fallback values applied to all projects (e.g., contribution_type, potential_overlap, support_source)
  - `dedup_key` (string): Configurable attribute key for duplicate project detection (default: `grant_info.award_number`)
- **CPOS organization config** in VA unit tree: Each site node carries `config.cpos_organization` with orgname, city, state (full name), and country
- **State abbreviation expansion**: `_state_abbrev_to_full()` converts 2-letter state codes to full names for CPOS organization metadata
- **ORCID iD field** added to VA and UMN person schemas
- **Schema tests** (`tests/test_schemas.py`): Validates schema file existence, JSON structure, and `load_schemas()` returns `"person"` key

### Changed
- **Renamed "user" to "person"** across the pipeline to align with Runway v2 resource types:
  - `schemas/__init__.py`: `load_schemas()` returns `"person"` key instead of `"user"`
  - Schema files renamed: `*_user_schema.json` → `*_person_schema.json`
  - Export output uses `"persons"` array key instead of `"users"` in both `main_va.py` and `main_ldap.py`
- **VA site naming**: Site names simplified from "City, ST" to just "City" (state info moved to `config.cpos_organization`)
- **Runway `import_bulk.py`**: CPOS auto-population gated behind `auto_populate_cpos` flag; dedup logic uses configurable `dedup_key`; `cpos_defaults` applied as fallbacks before auto-population; `"persons"`/`"users"` key normalization for backward compatibility
- **`main_va.py` / `main_ldap.py`**: Schema definitions loaded from shared JSON files instead of inline dicts; project attributes include pre-computed `cpos.*` fields
- All backward-compatible — old JSON files without new metadata keys work identically

### Fixed
- **VA unit_path double-prefix**: Removed root name from `unit_path` (validator prepends it), fixing 4697 validation errors on import
- **Summary print bug**: Fixed `schemas['user']` → `schemas['person']` in pack summary output

## 2026-02-25

### Added
- **PI override system** (`pi_overrides.json`): Manual corrections for PI department mappings that survive pipeline re-runs. Supports PI-level overrides (keyed by name) and department-level overrides (keyed by raw LDAP string). Applied in `--refine` before pattern matching.
- **27 department-level overrides** for admin units, core facilities, and research centers (e.g., `NSU Neurosurgery Dept Admin` -> Neurosurgery, `Analytical BiochemistryCC` -> BMBB, `CVM Research Office` -> Vet Clinical Sciences)
- **Helper file** `unmapped_none_pis.json` with 126 empty templates for PIs with no LDAP record, ready to fill in and merge
- **Verbose mapping source indicators**: `O` = PI override, `D` = dept override, `P` = pattern match
- `build_nested_structure.py` now uses pre-computed `school_official`/`department_official`/`division_official` from refine step, so overrides propagate automatically
- `magnetic resonance` pattern mapping CMRR faculty to Medical School / Radiology

### Changed
- **Word-boundary regex matching** for department patterns (replaces substring matching). Prevents false matches like "dent" in "president" or "son" in "resonance"
- Re-fetched 10 years of NIH data (FY2017-2026): 7,876 projects, 1,212 PIs

### Fixed
- `"son"` pattern no longer falsely maps Magnetic Resonance PIs to School of Nursing
- `"dent"` pattern no longer falsely maps admin titles (e.g., "Sr Vice President Health Sci") to School of Dentistry
- Blazar correctly mapped to Medical School / Pediatrics (via PI override)
- Crawford correctly mapped to Medical School / Medicine (via PI override)
- 10 CMRR faculty (Ugurbil, Mangia, Wu, Kay, etc.) correctly mapped to Radiology

## 2025-02-19

### Added
- Runway import step (`--pack`) combining org hierarchy and enriched projects into single import file
- LDAP name matching improvements: wildcard surname handling, post-filter scoring system
- Pipeline UX improvements: progress output, checkpoint saves

## 2025-02-18

### Added
- Division support for Department of Medicine (11 divisions)
- Refine step (`--refine`) for mapping LDAP departments to official UMN school/dept/division
- Expanded department mapping (100+ patterns) in `umn_structure.py`

### Fixed
- LDAP lookup matching wrong person by adding first name verification

## 2025-02-17

### Added
- Initial commit: NIH RePORTER fetch, LDAP and ORCID enrichment pipelines
- UMN organizational structure definition
- Nested structure builder
