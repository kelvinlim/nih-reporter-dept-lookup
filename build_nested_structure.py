"""
Build a nested JSON structure organized by University -> School -> Department
Uses official UMN organizational structure from UMN public sources
"""
import json
import os
from umn_structure import UMN_STRUCTURE, get_school_for_department

def build_nested_structure(pi_details_file):
    """
    Build nested JSON structure: University -> School -> Department -> PIs
    Using official UMN organizational mappings
    """
    with open(pi_details_file, 'r') as f:
        pi_details = json.load(f)
    
    # Start with official UMN structure template
    # Departments with divisions become nested dicts; departments without get empty PI lists
    base_structure = {}
    for uni_name, uni_data in UMN_STRUCTURE.items():
        base_structure[uni_name] = {}
        for campus_name, campus_data in uni_data.items():
            base_structure[uni_name][campus_name] = {}
            for school_name, dept_dict in campus_data.items():
                base_structure[uni_name][campus_name][school_name] = {}
                for dept_name, divisions in dept_dict.items():
                    if divisions:
                        # Department has divisions — create nested dict
                        base_structure[uni_name][campus_name][school_name][dept_name] = {
                            div: [] for div in divisions
                        }
                    else:
                        # No divisions — flat PI list
                        base_structure[uni_name][campus_name][school_name][dept_name] = []
    
    structure = base_structure
    
    # Track unmapped departments
    unmapped_depts = set()
    
    # Organize PIs by school, department, and optionally division
    for pi_name, details in pi_details.items():
        ldap_dept_str = details.get("department")
        rank = details.get("rank")
        ldap_dn = details.get("ldap_dn")

        # Use pre-computed official fields from refine step if available,
        # otherwise fall back to pattern matching
        school_name = details.get("school_official")
        normalized_dept = details.get("department_official")
        division = details.get("division_official")
        if school_name is None and normalized_dept is None:
            school_name, normalized_dept, division = get_school_for_department(ldap_dept_str)

        if not school_name:
            if ldap_dept_str:  # Only track non-None unmapped departments
                unmapped_depts.add(ldap_dept_str)
            school_name = "Other Departments"
            normalized_dept = ldap_dept_str or "Unknown"
            division = None

        campus = structure["University of Minnesota"]["UMN Twin Cities"]

        # Ensure school exists in structure
        if school_name not in campus:
            campus[school_name] = {}

        school_depts = campus[school_name]

        # Ensure department exists
        if normalized_dept not in school_depts:
            school_depts[normalized_dept] = [] if not division else {}

        pi_entry = {
            "name": pi_name,
            "rank": rank,
            "ldap_dn": ldap_dn
        }

        dept_node = school_depts[normalized_dept]

        if division and isinstance(dept_node, dict):
            # Place PI under the specific division
            if division not in dept_node:
                dept_node[division] = []
            dept_node[division].append(pi_entry)
        elif isinstance(dept_node, dict):
            # Department has divisions but PI didn't match one — put in dept-level "Other"
            if "Other" not in dept_node:
                dept_node["Other"] = []
            dept_node["Other"].append(pi_entry)
        else:
            # Department has no divisions — flat list
            dept_node.append(pi_entry)
    
    # Sort everyone alphabetically
    for uni_name, uni_data in structure.items():
        for campus_name, campus_data in uni_data.items():
            sorted_schools = {}
            for school_name in sorted(campus_data.keys()):
                school_data = campus_data[school_name]
                sorted_depts = {}
                for dept_name in sorted(school_data.keys()):
                    dept_node = school_data[dept_name]
                    if isinstance(dept_node, dict):
                        # Department with divisions — sort each division's PI list
                        sorted_divs = {}
                        for div_name in sorted(dept_node.keys()):
                            sorted_divs[div_name] = sorted(dept_node[div_name], key=lambda x: x["name"])
                        sorted_depts[dept_name] = sorted_divs
                    else:
                        # Flat PI list
                        sorted_depts[dept_name] = sorted(dept_node, key=lambda x: x["name"])
                sorted_schools[school_name] = sorted_depts
            structure[uni_name][campus_name] = sorted_schools
    
    return structure, unmapped_depts

def main():
    input_file = "pi_details_ldap.json"
    output_file = "nested_structure.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return
    
    print(f"Building nested structure from {input_file}...")
    print(f"Using official UMN organizational structure from umn_structure.py\n")
    
    structure, unmapped_depts = build_nested_structure(input_file)
    
    # Write to file
    with open(output_file, 'w') as f:
        json.dump(structure, f, indent=2)
    
    print(f"✓ Saved nested structure to {output_file}")
    
    # Print summary
    uni = structure["University of Minnesota"]
    campus = uni["UMN Twin Cities"]
    
    print(f"\nSummary:")
    print(f"  University: University of Minnesota")
    print(f"  Campus: UMN Twin Cities")
    print(f"  Schools: {len(campus)}")
    
    total_pis = 0
    total_depts = 0
    for school_name in sorted(campus.keys()):
        school_data = campus[school_name]
        num_depts = len(school_data)
        num_pis = 0
        for dept_node in school_data.values():
            if isinstance(dept_node, dict):
                num_pis += sum(len(pis) for pis in dept_node.values())
            else:
                num_pis += len(dept_node)
        total_pis += num_pis
        total_depts += num_depts
        print(f"    - {school_name}: {num_depts} departments, {num_pis} PIs")
    
    print(f"\n  Total Departments: {total_depts}")
    print(f"  Total PIs: {total_pis}")
    
    if unmapped_depts:
        print(f"\n⚠ Unmapped LDAP departments ({len(unmapped_depts)}):")
        for dept in sorted([d for d in unmapped_depts if d]):  # Filter out None
            print(f"    - {dept}")
        print(f"\nThese were placed in 'Other Departments'")
        print("To improve mapping, update umn_structure.py with additional patterns")

if __name__ == "__main__":
    main()
