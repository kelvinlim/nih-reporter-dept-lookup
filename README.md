# NIH Reporter Department Utility

This utility retrieves NIH grant data for a specific institution (default: University of Minnesota), organizes it by Principal Investigator (PI), and enriches it with PI details (Rank, Department, School).

It provides **two approaches** for PI enrichment:
- **LDAP Version** (Recommended): Uses UMN LDAP directory for accurate, real-time data
- **ORCID Version**: Uses ORCID Public API for institution-independent lookup

## Features

*   **Fetch Grants**: Retrieves 10 years of grant history from the NIH RePORTER API.
*   **Reorganize**: Groups projects by PI and Core Grant Number, sorted by project number.
*   **Enrich (LDAP)**: Lookups PI details using UMN LDAP directory (faster, more accurate for UMN).
*   **Enrich (ORCID)**: Lookups PI details using ORCID Public API (institution-independent).
*   **Join**: Merges all data into final datasets (JSON & CSV).
*   **Structure**: Generates hierarchical organization of UMN schools and departments.

## Setup

1.  **Clone the repository** (if not already done).
2.  **Set up a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **For LDAP Version**: Create a `.env` file with UMN LDAP credentials:
    ```bash
    cp .env.example .env
    # Edit .env with your UMN LDAP credentials
    ```
    Required variables:
    - `LDAP_SERVER`: LDAP server URL (e.g., `ldap://ldap.umn.edu:389`)
    - `BASE_DN`: Base Distinguished Name (e.g., `o=University of Minnesota,c=US`)
    - `BIND_DN`: Bind DN for authentication
    - `LDAP_LOGIN`: Username (e.g., `lnpiauth`)
    - `LDAP_PASSWORD`: Password

## Usage

### LDAP Version (Recommended)

The `main_ldap.py` script provides LDAP-based PI enrichment with single connection pooling.

#### 1. Fetch Raw Grant Data
```bash
python3 main_ldap.py --projects --years 10
```

#### 2. Reorganize Data
```bash
python3 main_ldap.py --reorganize
```

#### 3. Lookup PI Details via LDAP
```bash
python3 main_ldap.py --lookup
```
- Establishes a single LDAP connection and reuses it for all lookups (efficient)
- Falls back to anonymous bind if credentials fail
- Uses progressive LDAP filters with wildcard matching to handle credentials in surname fields (e.g., "Bellin MD") and verifies both first and last name to prevent wrong-person matches
- Caches results in `pi_details_ldap.json`
- Shows progress every 10 records

#### 4. Refine PI Details (Official Mapping)
```bash
python3 main_ldap.py --refine
```
- Maps each PI's raw LDAP department string to an official UMN school, normalized department, and optional division using patterns in `umn_structure.py`
- Adds `school_official`, `department_official`, and `division_official` fields to each entry in `pi_details_ldap.json`
- Reports unmapped departments so you can add new patterns

Use `--verbose` / `-v` to see each PI's mapping:
```bash
python3 main_ldap.py --refine --verbose
```

#### 5. Join Data
```bash
python3 main_ldap.py --join
```

#### 6. Pack for Runway Import
```bash
python3 main_ldap.py --pack
```
- Combines the UMN organizational unit hierarchy and enriched project data into a single JSON file for Runway import
- `units` key: school/department/division hierarchy (structure only, no PIs)
- `projects` key: projects organized by PI → Core Grant Number, with all enriched fields

**Output Files**:
- `pi_details_ldap.json`: Cache of PI details from LDAP (includes `school_official`, `department_official`, and `division_official` after refine)
- `final_department_data_ldap.json`: Full nested dataset with LDAP data
- `final_department_data_ldap.csv`: Flattened CSV with LDAP data
- `runway_import.json`: Combined units + projects for Runway import

### ORCID Version

The original `main.py` script uses ORCID for PI enrichment.

#### 1. Fetch Raw Grant Data
```bash
python3 main.py --projects --years 10
```

#### 2. Reorganize Data
```bash
python3 main.py --reorganize
```

#### 3. Lookup PI Details via ORCID
```bash
python3 main.py --lookup
```

#### 4. Join Data
```bash
python3 main.py --join
```

**Output Files**:
- `pi_details.json`: Cache of PI details from ORCID
- `final_department_data.json`: Full nested dataset with ORCID data
- `final_department_data.csv`: Flattened CSV with ORCID data

## Organizational Structure Files

### Source: `umn_structure.py`

The organizational hierarchy is defined in `umn_structure.py`, which was manually curated from UMN.edu public sources. It contains two key components:

1. **`UMN_STRUCTURE` dict** — The official UMN Twin Cities hierarchy of schools/colleges and their departments (e.g., Medical School → Anesthesiology, Neurology, etc.). This serves as the canonical source for `umn_schools_departments.json` and the department mapping used when building `nested_structure.json`.

2. **`get_school_for_department(dept_str)` function** — Maps free-text LDAP department strings to their official school, normalized department name, and optional division using 100+ case-insensitive keyword patterns. Returns a 3-tuple `(school, department, division)` where division is `None` for departments without divisions (e.g., `"anes"` → `("Medical School", "Anesthesiology", None)`, `"med cardiology"` → `("Medical School", "Medicine", "Cardiovascular")`). Departments that don't match any pattern fall back to `None` and are placed in "Other Departments" by the structure builder.

To add support for new or unmapped departments, add a new keyword pattern entry to the `dept_patterns` dict in `get_school_for_department()`.

### Generating `umn_schools_departments.json`

`build_schools_structure.py` reads the `UMN_STRUCTURE` dict from `umn_structure.py` and writes it out as a sorted, clean JSON file (without any PI data):

```bash
python3 build_schools_structure.py
```

**Output**: `umn_schools_departments.json`

**Structure**:
```
University of Minnesota
  └─ UMN Twin Cities
      ├─ Medical School (26 departments, Medicine has 11 divisions)
      ├─ College of Science and Engineering (11 departments)
      ├─ College of Liberal Arts (36 departments)
      ├─ School of Public Health (7 departments)
      ├─ School of Dentistry (7 departments)
      ├─ College of Food, Agricultural and Natural Resource Sciences (10 departments)
      ├─ Carlson School of Management (7 departments)
      ├─ Humphrey School of Public Affairs (1 department)
      ├─ School of Architecture (2 departments)
      ├─ School of Nursing (1 department)
      ├─ School of Pharmacy (6 departments)
      ├─ Graduate School (1 department)
      └─ Law School (1 department)
```

Departments map to a list of divisions (empty list if no divisions). Currently only the Department of Medicine has divisions populated.

### Nested Structure with PI Data

Generate hierarchical organization with PIs organized by school and department:

```bash
python3 build_nested_structure.py
```

**Output**: `nested_structure.json`

Each PI entry includes:
- `name`: Full name
- `rank`: Academic rank (Professor, Associate Professor, etc.)
- `ldap_dn`: LDAP Distinguished Name (LDAP version only)

## Output Files Reference

| File | Source | Description |
|------|--------|-------------|
| `projects_raw.json` | NIH RePORTER | Raw API response |
| `projects_by_pi.json` | Internal | Data organized by PI |
| `pi_details.json` | ORCID | PI details from ORCID |
| `pi_details_ldap.json` | LDAP | PI details from LDAP (cached) |
| `final_department_data.json` | ORCID + Projects | Complete dataset with ORCID |
| `final_department_data_ldap.json` | LDAP + Projects | Complete dataset with LDAP |
| `final_department_data.csv` | ORCID + Projects | Flattened CSV |
| `final_department_data_ldap.csv` | LDAP + Projects | Flattened CSV |
| `umn_schools_departments.json` | UMN Structure | Schools/departments only |
| `nested_structure.json` | UMN + LDAP | Hierarchical organization with PIs |
| `runway_import.json` | UMN + LDAP + Projects | Combined units + projects for Runway import |

## Data Source Information

### LDAP (ldap.umn.edu)
- **Source**: University of Minnesota LDAP Directory
- **Coverage**: All UMN-affiliated faculty
- **Attributes**: Name, Title (Rank), Department, Organization
- **Real-time**: Yes (cached with updates)
- **Rate Limiting**: None (efficient - reuses single connection)

### ORCID Public API
- **Source**: ORCID (https://orcid.org)
- **Coverage**: Researchers with ORCID profiles
- **Attributes**: Name, Employment Title, Department, Organization
- **Real-time**: Somewhat (last updated employment record)
- **Rate Limiting**: Yes (0.5s delay between requests)

## Technical Details

### LDAP Implementation
- Uses `ldap3` (pure Python, no system dependencies)
- Single connection pooling for efficiency
- Automatic fallback to anonymous bind
- Department name normalization using official UMN structure with division support
- Caching to avoid redundant LDAP queries

### Directory Organization Mapping
PIs are automatically mapped to official UMN schools and departments based on:
- LDAP department attributes
- Pattern matching for abbreviations (SPH, CSENG, Medical, etc.)
- Official UMN structure defined in `umn_structure.py`

Unmapped PIs are placed in "Other Departments" category.

## Examples

### Get all professors in Medical School
```python
import json
with open('nested_structure.json') as f:
    data = json.load(f)
med_school = data['University of Minnesota']['UMN Twin Cities']['Medical School']
for dept_name, dept_node in med_school.items():
    if isinstance(dept_node, dict):
        # Department with divisions (e.g., Medicine)
        for div_name, pis in dept_node.items():
            for pi in pis:
                if pi['rank'] == 'Professor':
                    print(f"{pi['name']} - {dept_name} / {div_name}")
    else:
        # Flat department
        for pi in dept_node:
            if pi['rank'] == 'Professor':
                print(f"{pi['name']} - {dept_name}")
```

### Export specific department
```python
import json
with open('nested_structure.json') as f:
    data = json.load(f)
cse = data['University of Minnesota']['UMN Twin Cities']['College of Science and Engineering']
cs_dept = cse.get('Computer Science and Engineering', [])
for pi in cs_dept:
    print(f"{pi['name']}: {pi['rank']}")
```

## Troubleshooting

### LDAP Connection Issues
- Ensure you have UMN network access or VPN enabled
- Check credentials in `.env` file
- Script will fall back to anonymous bind if credentials fail

### Missing LDAP Dependencies
- Uses `ldap3` (pure Python) - no apt-get required
- Install via: `pip install ldap3`

### ORCID Timeouts
- The ORCID lookup includes rate limiting (0.5s per request)
- With 500+ PIs, expect 5-10 minutes for full run
- Results are cached in `pi_details.json` for resume capability

