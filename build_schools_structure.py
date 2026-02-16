"""
Generate just the nested structure of UMN schools and departments without PI data
"""
import json
from umn_structure import UMN_STRUCTURE

def build_structure_only():
    """
    Build the nested structure showing University -> Campus -> Schools -> Departments
    without any PI information
    """
    structure = {}
    
    for uni_name, uni_data in UMN_STRUCTURE.items():
        structure[uni_name] = {}
        for campus_name, campus_data in uni_data.items():
            structure[uni_name][campus_name] = {}
            for school_name in sorted(campus_data.keys()):
                dept_list = sorted(campus_data[school_name])
                structure[uni_name][campus_name][school_name] = dept_list
    
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
    for school_name in sorted(campus.keys()):
        num_depts = len(campus[school_name])
        total_depts += num_depts
        print(f"    - {school_name}: {num_depts} departments")
    
    print(f"\n  Total Departments: {total_depts}")

if __name__ == "__main__":
    main()
