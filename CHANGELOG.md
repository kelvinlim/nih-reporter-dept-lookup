# Changelog

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
