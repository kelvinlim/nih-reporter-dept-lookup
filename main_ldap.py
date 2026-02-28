import argparse
import json
import os
import time
import pandas as pd
from fetch_grants import fetch_grants
from fetch_pi_details_ldap import get_pi_details, create_ldap_connection
from umn_structure import get_school_for_department
from build_schools_structure import build_structure_only

# File Constants
FILE_RAW = "projects_raw.json"
FILE_BY_PI = "projects_by_pi.json"
FILE_PI_DETAILS = "pi_details_ldap.json"
FILE_FINAL = "final_department_data_ldap.json"
FILE_FINAL_CSV = "final_department_data_ldap.csv"
FILE_RUNWAY = "runway_import.json"
FILE_OVERRIDES = "pi_overrides.json"

def extract_core_project_num(project_num):
    """
    Extracts core project number from full string.
    Example: '1U01DK127367-01' -> 'U01DK127367'
    Logic: Remove leading digit (Type) and everything after/including hyphen.
    """
    if not project_num:
        return "Unknown"
    
    # Split by hyphen to strip suffix
    base = project_num.split("-")[0]
    
    # Remove leading digit if present (Application Type Code)
    if base and base[0].isdigit():
        return base[1:]
    return base

def step_projects(years=0):
    """Fetch raw grants and save to FILE_RAW."""
    print(f"--- [Step 1] Fetching Projects ---")
    
    if years == 0:
        print("Fetching projects for the current year only.")
    else:
        print(f"Fetching projects for the last {years} years.")
        
    projects = fetch_grants(years=years)
    print(f"Total projects fetched: {len(projects)}")
    
    with open(FILE_RAW, "w") as f:
        json.dump(projects, f, indent=2)
    print(f"Saved raw data to {FILE_RAW}")

def step_reorganize():
    """Reorganize raw data by PI, then Core Grant, sorted by FY."""
    print(f"--- [Step 2] Reorganizing Data ---")
    if not os.path.exists(FILE_RAW):
        print(f"Error: {FILE_RAW} not found. Run --projects first.")
        return

    with open(FILE_RAW, "r") as f:
        raw_projects = json.load(f)

    # Structure: { "PI Name": { "CoreNum": [List of Projects] } }
    projects_by_pi = {}
    
    print(f"Processing {len(raw_projects)} records...")
    for project in raw_projects:
        pi_name = project.get("contact_pi_name")
        if not pi_name:
            pi_name = "Unknown"
        
        # Extract Core Number
        proj_num = project.get("project_num")
        core_num = extract_core_project_num(proj_num)
        project["core_project_num"] = core_num # Add field to record
        
        # Create project_num_clip (remove first digit if present)
        if proj_num and len(proj_num) > 0 and proj_num[0].isdigit():
             clip = proj_num[1:]
        else:
             clip = proj_num
        
        # Create new ordered dictionary with project_num_clip first
        new_project_entry = {"project_num_clip": clip}
        new_project_entry.update(project)
        
        if pi_name not in projects_by_pi:
            projects_by_pi[pi_name] = {}
            
        if core_num not in projects_by_pi[pi_name]:
            projects_by_pi[pi_name][core_num] = []
            
        projects_by_pi[pi_name][core_num].append(new_project_entry)

    # Sort each CoreNum's list by project_num_clip ascending
    for pi in projects_by_pi:
        for core_num in projects_by_pi[pi]:
            projects_by_pi[pi][core_num].sort(key=lambda x: x.get("project_num_clip") or "")

    with open(FILE_BY_PI, "w") as f:
        json.dump(projects_by_pi, f, indent=2)
    
    print(f"Reorganized data for {len(projects_by_pi)} PIs.")
    print(f"Saved to {FILE_BY_PI}")

def step_lookup(name_filter=None):
    """Enhance PI info using LDAP (UMN)."""
    print(f"--- [Step 3] PI Lookup (LDAP - UMN) ---")
    if not os.path.exists(FILE_BY_PI):
        print(f"Error: {FILE_BY_PI} not found. Run --reorganize first.")
        return

    with open(FILE_BY_PI, "r") as f:
        projects_by_pi = json.load(f)

    pi_details = {}

    if os.path.exists(FILE_PI_DETAILS):
        print(f"Found existing {FILE_PI_DETAILS}, loading cache...")
        with open(FILE_PI_DETAILS, "r") as f:
            pi_details = json.load(f)

    # Collect all PI names: contact PIs (dict keys) + co-PIs from principal_investigators
    all_pi_names = set(pi for pi in projects_by_pi if pi != "Unknown")
    co_pi_count = 0
    for pi_name, core_groups in projects_by_pi.items():
        for core_num, proj_list in core_groups.items():
            for proj in proj_list:
                for pi_entry in proj.get("principal_investigators") or []:
                    # Convert "First Middle Last" to "LAST, FIRST MIDDLE" format
                    last = pi_entry.get("last_name", "").strip().upper()
                    first = pi_entry.get("first_name", "").strip().upper()
                    middle = pi_entry.get("middle_name", "").strip().upper()
                    if not last:
                        continue
                    name = f"{last}, {first} {middle}".strip() if first else last
                    if name != "Unknown" and name not in all_pi_names:
                        all_pi_names.add(name)
                        co_pi_count += 1

    total_pis = len(all_pi_names)
    if co_pi_count:
        print(f"Found {co_pi_count} additional co-PIs from principal_investigators arrays")

    if name_filter:
        # Re-lookup PIs matching the name filter (case-insensitive)
        name_filter_lower = name_filter.lower()
        pis_to_process = [pi for pi in all_pi_names if name_filter_lower in pi.lower()]
        print(f"Filtering by name: \"{name_filter}\" — {len(pis_to_process)} matching PIs (will overwrite cached entries)")
    else:
        pis_to_process = [pi for pi in all_pi_names if pi not in pi_details]

    print(f"Total PIs: {total_pis}. Already cached: {len(pi_details)}. To process: {len(pis_to_process)}")
    
    # Create single LDAP connection for all lookups
    conn = create_ldap_connection()
    if not conn:
        print("Error: Could not establish LDAP connection")
        return
    
    count = 0
    try:
        for pi_name in pis_to_process:
            count += 1
            print(f"[{count}/{len(pis_to_process)}] {pi_name}")
            
            details = get_pi_details(pi_name, conn)
            if details:
                pi_details[pi_name] = {
                    "rank": details.get("rank"),
                    "department": details.get("department"),
                    "school": details.get("organization"),
                    "ldap_dn": details.get("dn")
                }
            else:
                 pi_details[pi_name] = {
                    "rank": None,
                    "department": None,
                    "school": None,
                    "ldap_dn": None
                }
            
            if count % 10 == 0:
                 with open(FILE_PI_DETAILS, "w") as f:
                    json.dump(pi_details, f, indent=2)
                    print(f"  (Checkpoint: saved {count} records)")
                    
            time.sleep(0.1)  # Small delay to avoid overwhelming LDAP server
    
    finally:
        # Always close the connection
        if conn:
            conn.unbind()
            print("✓ LDAP connection closed")

    with open(FILE_PI_DETAILS, "w") as f:
        json.dump(pi_details, f, indent=2)
    print(f"Saved PI LDAP details to {FILE_PI_DETAILS}")

def step_refine(verbose=False):
    """Refine PI details by mapping LDAP departments to official UMN school/department."""
    print(f"--- [Step 4] Refining PI Details (Official Mapping) ---")
    if not os.path.exists(FILE_PI_DETAILS):
        print(f"Error: {FILE_PI_DETAILS} not found. Run --lookup first.")
        return

    with open(FILE_PI_DETAILS, "r") as f:
        pi_details = json.load(f)

    # Load overrides if available
    pi_overrides = {}
    dept_overrides = {}
    if os.path.exists(FILE_OVERRIDES):
        with open(FILE_OVERRIDES, "r") as f:
            overrides = json.load(f)
        pi_overrides = overrides.get("pi_overrides", {})
        dept_overrides = overrides.get("department_overrides", {})
        print(f"Loaded overrides: {len(pi_overrides)} PI-level, {len(dept_overrides)} department-level")

    mapped = 0
    unmapped = 0
    overridden_pi = 0
    overridden_dept = 0
    unmapped_entries = []  # (pi_name, ldap_dept)

    for pi_name, details in pi_details.items():
        ldap_dept = details.get("department")
        source = "P"  # default: pattern match

        # Priority 1: PI-level override
        if pi_name in pi_overrides:
            ov = pi_overrides[pi_name]
            school_official = ov.get("school_official")
            dept_official = ov.get("department_official")
            div_official = ov.get("division_official")
            overridden_pi += 1
            source = "O"
        # Priority 2: Department-level override
        elif ldap_dept and ldap_dept in dept_overrides:
            ov = dept_overrides[ldap_dept]
            school_official = ov.get("school_official")
            dept_official = ov.get("department_official")
            div_official = ov.get("division_official")
            overridden_dept += 1
            source = "D"
        # Priority 3: Pattern matching
        else:
            school_official, dept_official, div_official = get_school_for_department(ldap_dept)

        if school_official:
            mapped += 1
        else:
            unmapped += 1
            unmapped_entries.append((pi_name, ldap_dept))

        details["school_official"] = school_official
        details["department_official"] = dept_official
        details["division_official"] = div_official

        if verbose:
            status = source if school_official else "✗"
            div_str = f" / {div_official}" if div_official else ""
            label = {
                "O": f"PI override",
                "D": f"dept override \"{ldap_dept}\"",
                "P": f"\"{ldap_dept}\""
            }.get(source, f"\"{ldap_dept}\"")
            print(f"  {status} {pi_name}: {label} → {school_official or 'UNMAPPED'} / {dept_official or 'N/A'}{div_str}")

    with open(FILE_PI_DETAILS, "w") as f:
        json.dump(pi_details, f, indent=2)

    print(f"\nMapped: {mapped}, Unmapped: {unmapped} (of {len(pi_details)} PIs)")
    if overridden_pi or overridden_dept:
        print(f"Overrides applied: {overridden_pi} PI-level, {overridden_dept} department-level")
    if unmapped_entries:
        print(f"\nUnmapped PIs ({len(unmapped_entries)}):")
        for pi_name, ldap_dept in sorted(unmapped_entries):
            print(f"  - {pi_name}: \"{ldap_dept or 'None'}\"")
        print(f"\nTo fix: add entries to {FILE_OVERRIDES} or patterns to umn_structure.py")
    print(f"Saved refined PI details to {FILE_PI_DETAILS}")

def step_join():
    """Join projects and PI details."""
    print(f"--- [Step 5] Joining Data ---")
    if not os.path.exists(FILE_BY_PI) or not os.path.exists(FILE_PI_DETAILS):
        print(f"Error: Missing input files. Ensure --reorganize and --lookup are run.")
        return

    with open(FILE_BY_PI, "r") as f:
        projects_by_pi = json.load(f)
        
    with open(FILE_PI_DETAILS, "r") as f:
        pi_details = json.load(f)
        
    final_data = [] 
    
    # Iterate Structure: PI -> CoreNum -> [Projects]
    for pi_name, core_groups in projects_by_pi.items():
        details = pi_details.get(pi_name, {})
        
        for core_num, projects in core_groups.items():
            for project in projects:
                enriched = project.copy()
                enriched["pi_rank"] = details.get("rank")
                enriched["pi_department"] = details.get("department")
                enriched["pi_school"] = details.get("school")
                enriched["pi_school_official"] = details.get("school_official")
                enriched["pi_department_official"] = details.get("department_official")
                enriched["pi_division_official"] = details.get("division_official")
                enriched["pi_ldap_dn"] = details.get("ldap_dn")
                
                final_data.append(enriched)

    with open(FILE_FINAL, "w") as f:
        json.dump(final_data, f, indent=2)
    print(f"Saved final JSON to {FILE_FINAL}")
    
    try:
        df = pd.json_normalize(final_data)
        df.to_csv(FILE_FINAL_CSV, index=False)
        print(f"Saved final CSV to {FILE_FINAL_CSV}")
    except Exception as e:
        print(f"Error saving CSV: {e}")

def _extract_x500_from_dn(ldap_dn):
    """Extract x500 ID from LDAP DN to construct email.

    Example: 'cn=Melena D Bellin MD (bell0130),ou=People,...' -> 'bell0130'
    """
    if not ldap_dn:
        return None
    import re
    match = re.search(r'\(([a-zA-Z0-9_]+)\)', ldap_dn)
    return match.group(1) if match else None


def _build_unit_tree(structure):
    """Convert flat UMN_STRUCTURE dict into nested children format for Runway import."""
    # structure is: { "University of Minnesota": { "UMN Twin Cities": { "School": { "Dept": [divs] } } } }
    uni_name = list(structure.keys())[0]  # "University of Minnesota"
    uni_data = structure[uni_name]

    root = {"name": uni_name, "children": []}

    for campus_name in sorted(uni_data.keys()):
        campus_node = {"name": campus_name, "children": []}
        campus_data = uni_data[campus_name]

        for school_name in sorted(campus_data.keys()):
            school_node = {"name": school_name, "children": []}
            dept_dict = campus_data[school_name]

            for dept_name in sorted(dept_dict.keys()):
                divisions = dept_dict[dept_name]
                if divisions:
                    dept_node = {"name": dept_name, "children": [
                        {"name": div} for div in sorted(divisions)
                    ]}
                else:
                    dept_node = {"name": dept_name}
                school_node["children"].append(dept_node)

            campus_node["children"].append(school_node)
        root["children"].append(campus_node)

    return root


def step_pack():
    """Pack into Runway bulk import v1.0 format (see BULK_IMPORT.md)."""
    print(f"--- [Step 6] Packing for Runway Import (v1.0) ---")
    if not os.path.exists(FILE_BY_PI) or not os.path.exists(FILE_PI_DETAILS):
        print(f"Error: Missing input files. Ensure --reorganize and --refine are run.")
        return

    with open(FILE_BY_PI, "r") as f:
        projects_by_pi = json.load(f)

    with open(FILE_PI_DETAILS, "r") as f:
        pi_details = json.load(f)

    # 1. Build nested unit tree from UMN_STRUCTURE
    flat_structure = build_structure_only()
    unit_tree = _build_unit_tree(flat_structure)

    # 2. Hierarchy levels (matches UMN structure)
    hierarchy_levels = ["University", "Campus", "College/School", "Department", "Division"]

    # 3. Schemas for user and project resource types
    schemas = {
        "user": {
            "general": {
                "_section": {"label": "General", "color": "blue"},
                "rank": {"type": "string", "title": "Academic Rank"},
                "orcid_id": {"type": "string", "title": "ORCID iD"},
                "is_investigator": {"type": "boolean", "title": "Investigator"}
            }
        },
        "project": {
            "grant_info": {
                "_section": {"label": "Grant Information", "color": "green"},
                "award_number": {"type": "string", "title": "Award Number"},
                "core_project_num": {"type": "string", "title": "Core Project Number"},
                "award_amount": {"type": "number", "title": "Award Amount"},
                "funding_agency": {"type": "string", "title": "Funding Agency"},
                "project_start_date": {"type": "string", "format": "date", "title": "Start Date"},
                "project_end_date": {"type": "string", "format": "date", "title": "End Date"},
                "budget_start": {"type": "string", "format": "date", "title": "Budget Start"},
                "budget_end": {"type": "string", "format": "date", "title": "Budget End"}
            }
        }
    }

    # 4. Build users and projects
    users = []
    projects = []
    email_set = set()
    skipped_no_dept = 0
    copi_fallback_count = 0
    skipped_no_email = 0

    for pi_name, core_groups in projects_by_pi.items():
        if pi_name == "Unknown":
            continue

        details = pi_details.get(pi_name, {})

        # Derive email from LDAP DN
        x500_id = _extract_x500_from_dn(details.get("ldap_dn"))
        if not x500_id:
            skipped_no_email += 1
            continue
        email = f"{x500_id}@umn.edu"

        # Build unit path from official mapping
        school = details.get("school_official")
        dept = details.get("department_official")
        division = details.get("division_official")

        if not school or not dept:
            skipped_no_dept += 1
            continue

        unit_path = ["UMN Twin Cities", school, dept]
        if division:
            unit_path.append(division)

        # Parse name: "LAST, FIRST MIDDLE" -> first_name, last_name
        parts = pi_name.split(", ", 1)
        last_name = parts[0].strip().title() if parts else pi_name.title()
        first_name = parts[1].strip().title() if len(parts) > 1 else ""
        # Trim middle name/initials from first_name
        first_name_parts = first_name.split()
        first_name = first_name_parts[0] if first_name_parts else first_name

        # Add user (skip duplicates)
        if email not in email_set:
            email_set.add(email)
            user_entry = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "unit_path": unit_path,
                "is_investigator": True,
                "attributes": {}
            }
            rank = details.get("rank")
            if rank:
                user_entry["attributes"]["general.rank"] = rank
            users.append(user_entry)

        # Add projects - take most recent fiscal year record per core grant
        for core_num, proj_list in core_groups.items():
            # Pick the most recent record (highest fiscal_year)
            proj_list_sorted = sorted(proj_list, key=lambda p: p.get("fiscal_year", 0), reverse=True)
            proj = proj_list_sorted[0]

            title = proj.get("project_title") or proj.get("title") or f"Grant {core_num}"

            # Format dates (strip time portion)
            start = (proj.get("project_start_date") or "")[:10]
            end = (proj.get("project_end_date") or "")[:10]
            budget_start = (proj.get("budget_start") or "")[:10]
            budget_end = (proj.get("budget_end") or "")[:10]

            abstract = (proj.get("abstract_text") or "").strip()

            # Build co-PI list from principal_investigators array
            co_pis = []
            for pi_entry in proj.get("principal_investigators") or []:
                # Convert "First Middle Last" to "LAST, FIRST MIDDLE" format
                copi_last = pi_entry.get("last_name", "").strip().upper()
                copi_first_raw = pi_entry.get("first_name", "").strip().upper()
                copi_middle = pi_entry.get("middle_name", "").strip().upper()
                if not copi_last:
                    continue
                copi_name = f"{copi_last}, {copi_first_raw} {copi_middle}".strip() if copi_first_raw else copi_last
                if copi_name == pi_name:
                    continue  # Skip contact PI (already the main PI)
                copi_details = pi_details.get(copi_name, {})
                copi_x500 = _extract_x500_from_dn(copi_details.get("ldap_dn"))
                copi_email = f"{copi_x500}@umn.edu" if copi_x500 else None
                if copi_email:
                    co_pis.append(copi_email)
                # Also add co-PI as a user if they have an email
                if copi_email and copi_email not in email_set:
                    copi_school = copi_details.get("school_official")
                    copi_dept = copi_details.get("department_official")
                    copi_div = copi_details.get("division_official")
                    if copi_school and copi_dept:
                        copi_unit_path = ["UMN Twin Cities", copi_school, copi_dept]
                        if copi_div:
                            copi_unit_path.append(copi_div)
                    else:
                        # Fallback for co-PIs with unmapped LDAP departments
                        copi_unit_path = ["UMN Twin Cities", "Other Departments"]
                        copi_fallback_count += 1
                    email_set.add(copi_email)
                    copi_parts = copi_name.split(", ", 1)
                    copi_last = copi_parts[0].strip().title() if copi_parts else copi_name.title()
                    copi_first = copi_parts[1].strip().title() if len(copi_parts) > 1 else ""
                    copi_first = copi_first.split()[0] if copi_first.split() else copi_first
                    copi_user = {
                        "email": copi_email,
                        "first_name": copi_first,
                        "last_name": copi_last,
                        "unit_path": copi_unit_path,
                        "is_investigator": True,
                        "attributes": {}
                    }
                    copi_rank = copi_details.get("rank")
                    if copi_rank:
                        copi_user["attributes"]["general.rank"] = copi_rank
                    users.append(copi_user)

            project_entry = {
                "title": title,
                "pi_email": email,
                "pi_name": pi_name,
                "status": "current",
                "unit_path": unit_path,
                "attributes": {
                    "grant_info.award_number": proj.get("project_num", ""),
                    "grant_info.core_project_num": core_num,
                    "grant_info.award_amount": proj.get("award_amount"),
                    "grant_info.funding_agency": "NIH",
                }
            }
            if co_pis:
                project_entry["co_pis"] = co_pis
            if abstract:
                project_entry["abstract"] = abstract
            if start:
                project_entry["attributes"]["grant_info.project_start_date"] = start
            if end:
                project_entry["attributes"]["grant_info.project_end_date"] = end
            if budget_start:
                project_entry["attributes"]["grant_info.budget_start"] = budget_start
            if budget_end:
                project_entry["attributes"]["grant_info.budget_end"] = budget_end

            projects.append(project_entry)

    # Add "Other Departments" unit to the tree if any co-PIs needed the fallback
    if copi_fallback_count > 0:
        campus_node = unit_tree.get("children", [{}])[0]  # "UMN Twin Cities"
        campus_node.setdefault("children", []).append({"name": "Other Departments"})

    # 5. Assemble final import file
    from datetime import date
    runway_data = {
        "metadata": {
            "version": "1.0",
            "description": "University of Minnesota NIH-funded researchers and grants",
            "created": str(date.today()),
            "source": "nih-reporter-dept-lookup LDAP pipeline",
            "effort_defaults": {
                "create_effort": True,
                "default_person_months": 3.0,
                "period_type": "calendar"
            }
        },
        "hierarchy_levels": hierarchy_levels,
        "units": unit_tree,
        "schemas": schemas,
        "users": users,
        "projects": projects,
    }

    with open(FILE_RUNWAY, "w") as f:
        json.dump(runway_data, f, indent=2)
    print(f"Saved Runway import file to {FILE_RUNWAY}")

    # Summary
    print(f"\nSummary:")
    print(f"  Hierarchy: {' -> '.join(hierarchy_levels)}")
    print(f"  Users: {len(users)} investigators")
    print(f"  Projects: {len(projects)} grants (most recent per core number)")
    print(f"  Schemas: user ({len(schemas['user'])} categories), project ({len(schemas['project'])} categories)")
    if skipped_no_email:
        print(f"  Skipped (no email): {skipped_no_email} PIs")
    if skipped_no_dept:
        print(f"  Skipped (no dept mapping): {skipped_no_dept} PIs")
    if copi_fallback_count:
        print(f"  Co-PIs in Other Departments (unmapped): {copi_fallback_count}")

def main():
    parser = argparse.ArgumentParser(description="NIH Reporter Department Utility (LDAP Version)")
    parser.add_argument("--projects", action="store_true", help="Fetch raw grants from NIH RePORTER")
    parser.add_argument("--years", type=int, default=0, help="Number of years to fetch (0 for current year, N for last N years)")
    parser.add_argument("--reorganize", action="store_true", help="Organize grants by PI")
    parser.add_argument("--lookup", action="store_true", help="Lookup PI details on LDAP (UMN)")
    parser.add_argument("--name", type=str, default=None, help="Re-lookup only PIs matching this name (used with --lookup)")
    parser.add_argument("--refine", action="store_true", help="Map LDAP departments to official UMN school/department")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed mapping output (used with --refine)")
    parser.add_argument("--join", action="store_true", help="Join grants and PI details")
    parser.add_argument("--pack", action="store_true", help="Pack units + projects into single Runway import file")

    args = parser.parse_args()

    if args.projects:
        step_projects(years=args.years)

    if args.reorganize:
        step_reorganize()

    if args.lookup:
        step_lookup(name_filter=args.name)

    if args.refine:
        step_refine(verbose=args.verbose)

    if args.join:
        step_join()

    if args.pack:
        step_pack()

    if not any(vars(args).values()):
        parser.print_help()

if __name__ == "__main__":
    main()
