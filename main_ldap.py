import argparse
import json
import os
import time
import pandas as pd
from fetch_grants import fetch_grants
from fetch_pi_details_ldap import get_pi_details, create_ldap_connection
from umn_structure import get_school_for_department

# File Constants
FILE_RAW = "projects_raw.json"
FILE_BY_PI = "projects_by_pi.json"
FILE_PI_DETAILS = "pi_details_ldap.json"
FILE_FINAL = "final_department_data_ldap.json"
FILE_FINAL_CSV = "final_department_data_ldap.csv"

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

def step_lookup():
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
            
    # projects_by_pi keys are PI Names
    total_pis = len(projects_by_pi)
    pis_to_process = [pi for pi in projects_by_pi if pi not in pi_details and pi != "Unknown"]
    
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

    mapped = 0
    unmapped = 0
    unmapped_depts = set()

    for pi_name, details in pi_details.items():
        ldap_dept = details.get("department")
        school_official, dept_official, div_official = get_school_for_department(ldap_dept)

        if school_official:
            mapped += 1
        else:
            unmapped += 1
            if ldap_dept:
                unmapped_depts.add(ldap_dept)

        details["school_official"] = school_official
        details["department_official"] = dept_official
        details["division_official"] = div_official

        if verbose:
            status = "✓" if school_official else "✗"
            div_str = f" / {div_official}" if div_official else ""
            print(f"  {status} {pi_name}: \"{ldap_dept}\" → {school_official or 'UNMAPPED'} / {dept_official or 'N/A'}{div_str}")

    with open(FILE_PI_DETAILS, "w") as f:
        json.dump(pi_details, f, indent=2)

    print(f"\nMapped: {mapped}, Unmapped: {unmapped} (of {len(pi_details)} PIs)")
    if unmapped_depts:
        print(f"\nUnmapped LDAP departments ({len(unmapped_depts)}):")
        for dept in sorted(unmapped_depts):
            print(f"  - {dept}")
        print("To improve mapping, add patterns to umn_structure.py")
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

def main():
    parser = argparse.ArgumentParser(description="NIH Reporter Department Utility (LDAP Version)")
    parser.add_argument("--projects", action="store_true", help="Fetch raw grants from NIH RePORTER")
    parser.add_argument("--years", type=int, default=0, help="Number of years to fetch (0 for current year, N for last N years)")
    parser.add_argument("--reorganize", action="store_true", help="Organize grants by PI")
    parser.add_argument("--lookup", action="store_true", help="Lookup PI details on LDAP (UMN)")
    parser.add_argument("--refine", action="store_true", help="Map LDAP departments to official UMN school/department")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed mapping output (used with --refine)")
    parser.add_argument("--join", action="store_true", help="Join grants and PI details")
    
    args = parser.parse_args()
    
    if args.projects:
        step_projects(years=args.years)
    
    if args.reorganize:
        step_reorganize()
        
    if args.lookup:
        step_lookup()

    if args.refine:
        step_refine(verbose=args.verbose)

    if args.join:
        step_join()

    if not any(vars(args).values()):
        parser.print_help()

if __name__ == "__main__":
    main()
