"""
Generate just the nested structure of UMN schools and departments without PI data
"""
import json
from umn_structure import UMN_STRUCTURE

def build_structure_only():
    """
    Build the nested structure showing University -> Campus -> Schools -> Departments (-> Divisions)
    without any PI information.
    Departments map to a list of divisions (empty list if no divisions).
    """
    structure = {}

    for uni_name, uni_data in UMN_STRUCTURE.items():
        structure[uni_name] = {}
        for campus_name, campus_data in uni_data.items():
            structure[uni_name][campus_name] = {}
            for school_name in sorted(campus_data.keys()):
                dept_dict = campus_data[school_name]
                sorted_depts = {}
                for dept_name in sorted(dept_dict.keys()):
                    sorted_depts[dept_name] = sorted(dept_dict[dept_name])
                structure[uni_name][campus_name][school_name] = sorted_depts

    return structure

def main():
    print("Building UMN organizational structure (schools and departments only)...")
    structure = build_structure_only()
    
    # Save to file
    with open('umn_schools_departments.json', 'w') as f:
        json.dump(structure, f, indent=2)
    
    print("✓ Saved to umn_schools_departments.json")
    
    # Print summary
    uni = structure["University of Minnesota"]
    campus = uni["UMN Twin Cities"]
    
    print(f"\nSummary:")
    print(f"  University: University of Minnesota")
    print(f"  Campus: UMN Twin Cities")
    print(f"  Schools: {len(campus)}")
    
    total_depts = 0
    total_divs = 0
    for school_name in sorted(campus.keys()):
        dept_dict = campus[school_name]
        num_depts = len(dept_dict)
        num_divs = sum(len(divs) for divs in dept_dict.values())
        total_depts += num_depts
        total_divs += num_divs
        div_info = f", {num_divs} divisions" if num_divs else ""
        print(f"    - {school_name}: {num_depts} departments{div_info}")

    print(f"\n  Total Departments: {total_depts}")
    if total_divs:
        print(f"  Total Divisions: {total_divs}")

if __name__ == "__main__":
    main()
