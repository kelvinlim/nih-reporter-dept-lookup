"""
Official UMN Twin Cities Schools and Colleges Organizational Structure
Based on UMN.edu public sources
"""

UMN_STRUCTURE = {
    "University of Minnesota": {
        "UMN Twin Cities": {
            "College of Food, Agricultural and Natural Resource Sciences": {
                "Applied Economics": [],
                "Biosystems and Agricultural Engineering": [],
                "Entomology": [],
                "Food Science and Nutrition": [],
                "Forest Resources": [],
                "Plant and Soil Sciences": [],
                "Veterinary Clinical Sciences": [],
                "Veterinary Diagnostic and Biological Sciences": [],
                "Veterinary Population Medicine": [],
                "School of Natural Resources": []
            },
            "College of Liberal Arts": {
                "African American and African Studies": [],
                "American Studies": [],
                "Anthropology": [],
                "Art": [],
                "Asian Languages and Literatures": [],
                "Central Asian Studies": [],
                "Classics": [],
                "Communication Studies": [],
                "Comparative Literature": [],
                "East Asian Studies": [],
                "Economics": [],
                "English": [],
                "European Studies": [],
                "French and Italian": [],
                "German, Scandinavian and Dutch": [],
                "Germano-Nordic Studies": [],
                "Global Studies": [],
                "History": [],
                "Honors Program": [],
                "Humanities": [],
                "Jewish Studies": [],
                "Lesbian, Gay, Bisexual, Transgender, Queer Studies": [],
                "Linguistics": [],
                "Music": [],
                "Philosophy": [],
                "Political Science": [],
                "Psychology": [],
                "Religious Studies": [],
                "Scandinavian Studies": [],
                "Slavic and East European Studies": [],
                "Sociology": [],
                "Spanish and Portuguese": [],
                "Statistics": [],
                "Studio Art": [],
                "Theatre Arts and Dance": [],
                "Women's Studies": []
            },
            "College of Science and Engineering": {
                "Aerospace Engineering and Mechanics": [],
                "Biomedical Engineering": [],
                "Chemical Engineering and Materials Science": [],
                "Chemistry": [],
                "Civil, Environmental and Geo-Engineering": [],
                "Geological Sciences": [],
                "Industrial and Systems Engineering": [],
                "Mathematics": [],
                "Mechanical Engineering": [],
                "Physics": [],
                "Computer Science and Engineering": []
            },
            "Carlson School of Management": {
                "Accounting": [],
                "Business and Management": [],
                "Finance": [],
                "Management Information Systems": [],
                "Marketing and Logistics Management": [],
                "Organizational Behavior and Human Resources": [],
                "Strategic Management and Entrepreneurship": []
            },
            "Medical School": {
                "Anesthesiology": [],
                "Biochemistry, Molecular Biology and Biophysics": [],
                "Dean's Office": [],
                "Dermatology": [],
                "Emergency Medicine": [],
                "Family Medicine and Community Health": [],
                "Genetics, Cell Biology and Development": [],
                "Immunology": [],
                "Medicine": [
                    "Cardiovascular",
                    "Diabetes, Endocrinology and Metabolism",
                    "Gastroenterology, Hepatology and Nutrition",
                    "General Internal Medicine",
                    "Hematology, Oncology and Transplantation",
                    "Hospital Medicine",
                    "Infectious Diseases and International Medicine",
                    "Molecular Medicine",
                    "Nephrology and Hypertension",
                    "Pulmonary, Allergy, Critical Care and Sleep Medicine",
                    "Rheumatic and Autoimmune Diseases"
                ],
                "Microbiology and Immunology": [],
                "Neurology": [],
                "Neuroscience": [],
                "Obstetrics, Gynecology and Reproductive Medicine": [],
                "Oncology": [],
                "Ophthalmology": [],
                "Organizational Leadership, Policy and Development": [],
                "Orthopaedic Surgery": [],
                "Otolaryngology": [],
                "Pathology": [],
                "Pediatrics": [],
                "Pharmacology": [],
                "Physiology": [],
                "Psychiatry": [],
                "Radiology": [],
                "Surgery": [],
                "Urology": []
            },
            "School of Dentistry": {
                "Endodontics": [],
                "Oral and Maxillofacial Surgery": [],
                "Oral and Maxillofacial Pathology": [],
                "Oral Biology and Diagnostic Sciences": [],
                "Periodontics, Prosthodontics and Implant Dentistry": [],
                "Pediatric Dentistry": [],
                "Restorative Dentistry": []
            },
            "School of Nursing": {
                "Nursing": []
            },
            "School of Public Health": {
                "Biostatistics": [],
                "Division of Epidemiology and Community Health": [],
                "Division of Environmental Health Sciences": [],
                "Division of Health Policy and Management": [],
                "Maternal and Child Health": [],
                "Public Health": [],
                "School of Public Health": []
            },
            "School of Pharmacy": {
                "Medicinal Chemistry": [],
                "Pharmaceutics": [],
                "Pharmaceutical Chemistry": [],
                "Pharmacognosy": [],
                "Pharmacology": [],
                "Pharmacy": []
            },
            "School of Architecture": {
                "Architecture": [],
                "Urban Design": []
            },
            "Humphrey School of Public Affairs": {
                "Public Policy": []
            },
            "Law School": {
                "Law": []
            },
            "Graduate School": {
                "Graduate Studies": []
            }
        }
    }
}

def get_school_for_department(dept_str):
    """
    Find the school for a given department string from LDAP.
    Returns (school_name, normalized_department_name, division_name) tuple.
    division_name is None when the department has no divisions or the
    specific division could not be determined.
    """
    if not dept_str:
        return None, None, None

    dept_lower = dept_str.lower()

    # Create a mapping of keywords/patterns to (school, normalized_dept, division)
    # Order matters: more specific patterns must appear before generic ones.
    dept_patterns = {
        # CFANS
        "entomology": ("College of Food, Agricultural and Natural Resource Sciences", "Entomology", None),
        "food sci": ("College of Food, Agricultural and Natural Resource Sciences", "Food Science and Nutrition", None),
        "food/agr": ("College of Food, Agricultural and Natural Resource Sciences", "Food Science and Nutrition", None),
        "agricultural": ("College of Food, Agricultural and Natural Resource Sciences", "Applied Economics", None),
        "agronomy": ("College of Food, Agricultural and Natural Resource Sciences", "Plant and Soil Sciences", None),
        "forest": ("College of Food, Agricultural and Natural Resource Sciences", "Forest Resources", None),
        "veterinary": ("College of Food, Agricultural and Natural Resource Sciences", "Veterinary Clinical Sciences", None),
        "cfans": ("College of Food, Agricultural and Natural Resource Sciences", "Other", None),

        # CLA
        "lib arts": ("College of Liberal Arts", "Other", None),
        "cla": ("College of Liberal Arts", "Other", None),
        "art ": ("College of Liberal Arts", "Art", None),
        "music": ("College of Liberal Arts", "Music", None),
        "english": ("College of Liberal Arts", "English", None),
        "history": ("College of Liberal Arts", "History", None),
        "sociology": ("College of Liberal Arts", "Sociology", None),
        "philosophy": ("College of Liberal Arts", "Philosophy", None),
        "anthropology": ("College of Liberal Arts", "Anthropology", None),
        "psychology": ("College of Liberal Arts", "Psychology", None),
        "political science": ("College of Liberal Arts", "Political Science", None),
        "economics": ("College of Liberal Arts", "Economics", None),
        "communication": ("College of Liberal Arts", "Communication Studies", None),
        "theatre": ("College of Liberal Arts", "Theatre Arts and Dance", None),
        "dance": ("College of Liberal Arts", "Theatre Arts and Dance", None),
        "linguistics": ("College of Liberal Arts", "Linguistics", None),
        "german": ("College of Liberal Arts", "German, Scandinavian and Dutch", None),
        "scandinavian": ("College of Liberal Arts", "Scandinavian Studies", None),
        "french": ("College of Liberal Arts", "French and Italian", None),
        "italian": ("College of Liberal Arts", "French and Italian", None),
        "spanish": ("College of Liberal Arts", "Spanish and Portuguese", None),
        "portuguese": ("College of Liberal Arts", "Spanish and Portuguese", None),
        "asian": ("College of Liberal Arts", "Asian Languages and Literatures", None),
        "classics": ("College of Liberal Arts", "Classics", None),
        "religious": ("College of Liberal Arts", "Religious Studies", None),

        # CSE
        "biomedical eng": ("College of Science and Engineering", "Biomedical Engineering", None),
        "cseng chemical": ("College of Science and Engineering", "Chemical Engineering and Materials Science", None),
        "cseng chemistry": ("College of Science and Engineering", "Chemistry", None),
        "chemistry admin": ("College of Science and Engineering", "Chemistry", None),
        "cseng civil": ("College of Science and Engineering", "Civil, Environmental and Geo-Engineering", None),
        "cseng mech": ("College of Science and Engineering", "Mechanical Engineering", None),
        "mechanical eng": ("College of Science and Engineering", "Mechanical Engineering", None),
        "computer science": ("College of Science and Engineering", "Computer Science and Engineering", None),
        "cseng aerospace": ("College of Science and Engineering", "Aerospace Engineering and Mechanics", None),
        "industrial system": ("College of Science and Engineering", "Industrial and Systems Engineering", None),
        "geology": ("College of Science and Engineering", "Geological Sciences", None),
        "physics": ("College of Science and Engineering", "Physics", None),
        "mathematics": ("College of Science and Engineering", "Mathematics", None),
        "cseng": ("College of Science and Engineering", "Other", None),
        "science/eng": ("College of Science and Engineering", "Other", None),
        "statistics": ("College of Science and Engineering", "Mathematics", None),
        "bio science": ("College of Science and Engineering", "Physics", None),
        "cbs": ("College of Science and Engineering", "Physics", None),
        "medicinal chemistry": ("College of Science and Engineering", "Chemistry", None),

        # Carlson
        "carlson": ("Carlson School of Management", "Business and Management", None),
        "management": ("Carlson School of Management", "Business and Management", None),
        "accounting": ("Carlson School of Management", "Accounting", None),
        "finance": ("Carlson School of Management", "Finance", None),
        "bus/econ": ("Carlson School of Management", "Business and Management", None),

        # Medical School — Department of Medicine divisions (must precede generic "medicine")
        "med cardiology": ("Medical School", "Medicine", "Cardiovascular"),
        "med endocrine": ("Medical School", "Medicine", "Diabetes, Endocrinology and Metabolism"),
        "med gastro": ("Medical School", "Medicine", "Gastroenterology, Hepatology and Nutrition"),
        "med general": ("Medical School", "Medicine", "General Internal Medicine"),
        "med hema": ("Medical School", "Medicine", "Hematology, Oncology and Transplantation"),
        "med inf disease": ("Medical School", "Medicine", "Infectious Diseases and International Medicine"),
        "med nephrology": ("Medical School", "Medicine", "Nephrology and Hypertension"),
        "med pulmonary": ("Medical School", "Medicine", "Pulmonary, Allergy, Critical Care and Sleep Medicine"),
        "med rheumatic": ("Medical School", "Medicine", "Rheumatic and Autoimmune Diseases"),
        "med veteran": ("Medical School", "Medicine", None),
        # Medical School — other departments
        "medicine": ("Medical School", "Medicine", None),
        "med sch": ("Medical School", "Medicine", None),
        "anesthesiology": ("Medical School", "Anesthesiology", None),
        "anes": ("Medical School", "Anesthesiology", None),
        "dermatology": ("Medical School", "Dermatology", None),
        "neurology": ("Medical School", "Neurology", None),
        "neuroscience": ("Medical School", "Neuroscience", None),
        "oncology": ("Medical School", "Oncology", None),
        "pediatrics": ("Medical School", "Pediatrics", None),
        "peds": ("Medical School", "Pediatrics", None),
        "psychiatry": ("Medical School", "Psychiatry", None),
        "radiology": ("Medical School", "Radiology", None),
        "surgery": ("Medical School", "Surgery", None),
        "internal medicine": ("Medical School", "Medicine", "General Internal Medicine"),
        "obstetrics": ("Medical School", "Obstetrics, Gynecology and Reproductive Medicine", None),
        "ob/gyn": ("Medical School", "Obstetrics, Gynecology and Reproductive Medicine", None),
        "orthop": ("Medical School", "Orthopaedic Surgery", None),
        "otolaryngology": ("Medical School", "Otolaryngology", None),
        "urology": ("Medical School", "Urology", None),
        "ophthalmology": ("Medical School", "Ophthalmology", None),
        "pharmacology": ("Medical School", "Pharmacology", None),
        "pathology": ("Medical School", "Pathology", None),
        "microbiology": ("Medical School", "Microbiology and Immunology", None),
        "immunology": ("Medical School", "Immunology", None),
        "biochemistry": ("Medical School", "Biochemistry, Molecular Biology and Biophysics", None),
        "bmbb": ("Medical School", "Biochemistry, Molecular Biology and Biophysics", None),
        "genetics": ("Medical School", "Genetics, Cell Biology and Development", None),
        "physiology": ("Medical School", "Physiology", None),
        "fammed": ("Medical School", "Family Medicine and Community Health", None),
        "family medicine": ("Medical School", "Family Medicine and Community Health", None),
        "dmed": ("Medical School", "Family Medicine and Community Health", None),
        "emergency": ("Medical School", "Emergency Medicine", None),
        "dent biomaterials": ("Medical School", "Biomaterials", None),
        "dent molecular": ("Medical School", "Microbiology and Immunology", None),
        "experimental clinical pharm": ("Medical School", "Pharmacology", None),
        "experimental & clinical pharm": ("Medical School", "Pharmacology", None),
        "health informatics": ("Medical School", "Medicine", None),
        "ms dean": ("Medical School", "Dean's Office", None),
        "ms md/phd": ("Medical School", "Dean's Office", None),
        "ms research": ("Medical School", "Dean's Office", None),

        # Dentistry
        "dent basic": ("School of Dentistry", "Oral Biology and Diagnostic Sciences", None),
        "dent periodontics": ("School of Dentistry", "Periodontics, Prosthodontics and Implant Dentistry", None),
        "endodontics": ("School of Dentistry", "Endodontics", None),
        "oral surgery": ("School of Dentistry", "Oral and Maxillofacial Surgery", None),
        "lmp": ("School of Dentistry", "Oral and Maxillofacial Pathology", None),
        "gcd": ("School of Dentistry", "Oral Biology and Diagnostic Sciences", None),
        "dent": ("School of Dentistry", "Oral Biology and Diagnostic Sciences", None),
        "dentistry": ("School of Dentistry", "Oral Biology and Diagnostic Sciences", None),

        # Nursing
        "nursing": ("School of Nursing", "Nursing", None),
        "son": ("School of Nursing", "Nursing", None),

        # Public Health
        "sph": ("School of Public Health", "Division of Epidemiology and Community Health", None),
        "public hlth": ("School of Public Health", "Division of Epidemiology and Community Health", None),
        "epidemiology": ("School of Public Health", "Division of Epidemiology and Community Health", None),
        "biostatistics": ("School of Public Health", "Biostatistics", None),
        "environmental health": ("School of Public Health", "Division of Environmental Health Sciences", None),
        "health policy": ("School of Public Health", "Division of Health Policy and Management", None),

        # Pharmacy
        "pharmacy": ("School of Pharmacy", "Pharmacy", None),
        "cop": ("School of Pharmacy", "Pharmacy", None),

        # Architecture
        "architecture": ("School of Architecture", "Architecture", None),
        "design": ("School of Architecture", "Architecture", None),

        # Humphrey School of Public Affairs
        "hhh": ("Humphrey School of Public Affairs", "Public Policy", None),

        # Other Colleges
        "kinesiology": ("College of Liberal Arts", "Psychology", None),
        "ed psych": ("College of Liberal Arts", "Psychology", None),
        "cehd": ("College of Liberal Arts", "Education", None),
        "educ/hum": ("College of Liberal Arts", "Education", None),
        "speech-language": ("College of Liberal Arts", "Communication Studies", None),
        "physical therapy": ("College of Liberal Arts", "Psychology", None),
        "child development": ("College of Liberal Arts", "Psychology", None),
        "fsos": ("College of Liberal Arts", "Sociology", None),
        "grad dean": ("Graduate School", "Graduate Studies", None),
        "grad school": ("Graduate School", "Graduate Studies", None),
        "law school": ("Law School", "Law", None),
    }

    # Try to match patterns
    for pattern, (school, dept, division) in dept_patterns.items():
        if pattern in dept_lower:
            return school, dept, division

    # Default fallback
    return None, dept_str, None

if __name__ == "__main__":
    # Print structure for reference
    import json
    print(json.dumps(UMN_STRUCTURE, indent=2))
