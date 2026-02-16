"""
Official UMN Twin Cities Schools and Colleges Organizational Structure
Based on UMN.edu public sources
"""

UMN_STRUCTURE = {
    "University of Minnesota": {
        "UMN Twin Cities": {
            "College of Food, Agricultural and Natural Resource Sciences": [
                "Applied Economics",
                "Biosystems and Agricultural Engineering",
                "Entomology",
                "Food Science and Nutrition",
                "Forest Resources",
                "Plant and Soil Sciences",
                "Veterinary Clinical Sciences",
                "Veterinary Diagnostic and Biological Sciences",
                "Veterinary Population Medicine",
                "School of Natural Resources"
            ],
            "College of Liberal Arts": [
                "African American and African Studies",
                "American Studies",
                "Anthropology",
                "Art",
                "Asian Languages and Literatures",
                "Central Asian Studies",
                "Classics",
                "Communication Studies",
                "Comparative Literature",
                "East Asian Studies",
                "Economics",
                "English",
                "European Studies",
                "French and Italian",
                "German, Scandinavian and Dutch",
                "Germano-Nordic Studies",
                "Global Studies",
                "History",
                "Honors Program",
                "Humanities",
                "Jewish Studies",
                "Lesbian, Gay, Bisexual, Transgender, Queer Studies",
                "Linguistics",
                "Music",
                "Philosophy",
                "Political Science",
                "Psychology",
                "Religious Studies",
                "Scandinavian Studies",
                "Slavic and East European Studies",
                "Sociology",
                "Spanish and Portuguese",
                "Statistics",
                "Studio Art",
                "Theatre Arts and Dance",
                "Women's Studies"
            ],
            "College of Science and Engineering": [
                "Aerospace Engineering and Mechanics",
                "Biomedical Engineering",
                "Chemical Engineering and Materials Science",
                "Chemistry",
                "Civil, Environmental and Geo-Engineering",
                "Geological Sciences",
                "Industrial and Systems Engineering",
                "Mathematics",
                "Mechanical Engineering",
                "Physics",
                "Computer Science and Engineering"
            ],
            "Carlson School of Management": [
                "Accounting",
                "Business and Management",
                "Finance",
                "Management Information Systems",
                "Marketing and Logistics Management",
                "Organizational Behavior and Human Resources",
                "Strategic Management and Entrepreneurship"
            ],
            "Medical School": [
                "Anesthesiology",
                "Biochemistry, Molecular Biology and Biophysics",
                "Dermatology",
                "Emergency Medicine",
                "Family Medicine and Community Health",
                "General Internal Medicine",
                "Genetics, Cell Biology and Development",
                "Immunology",
                "Medicine",
                "Microbiology and Immunology",
                "Neurology",
                "Neuroscience",
                "Obstetrics, Gynecology and Reproductive Medicine",
                "Oncology",
                "Ophthalmology",
                "Organizational Leadership, Policy and Development",
                "Orthopaedic Surgery",
                "Otolaryngology",
                "Pathology",
                "Pediatrics",
                "Pharmacology",
                "Physiology",
                "Psychiatry",
                "Radiology",
                "Surgery",
                "Urology"
            ],
            "School of Dentistry": [
                "Endodontics",
                "Oral and Maxillofacial Surgery",
                "Oral and Maxillofacial Pathology",
                "Oral Biology and Diagnostic Sciences",
                "Periodontics, Prosthodontics and Implant Dentistry",
                "Pediatric Dentistry",
                "Restorative Dentistry"
            ],
            "School of Nursing": [
                "Nursing"
            ],
            "School of Public Health": [
                "Biostatistics",
                "Division of Epidemiology and Community Health",
                "Division of Environmental Health Sciences",
                "Division of Health Policy and Management",
                "Maternal and Child Health",
                "Public Health",
                "School of Public Health"
            ],
            "School of Pharmacy": [
                "Medicinal Chemistry",
                "Pharmaceutics",
                "Pharmaceutical Chemistry",
                "Pharmacognosy",
                "Pharmacology",
                "Pharmacy"
            ],
            "School of Architecture": [
                "Architecture",
                "Urban Design"
            ],
            "Law School": [
                "Law"
            ],
            "Graduate School": [
                "Graduate Studies"
            ]
        }
    }
}

def get_school_for_department(dept_str):
    """
    Find the school for a given department string from LDAP.
    Returns (school_name, normalized_department_name) tuple
    """
    if not dept_str:
        return None, None
    
    dept_lower = dept_str.lower()
    
    # Create a mapping of keywords/patterns to (school, normalized_dept)
    dept_patterns = {
        # CFANS
        "entomology": ("College of Food, Agricultural and Natural Resource Sciences", "Entomology"),
        "food sci": ("College of Food, Agricultural and Natural Resource Sciences", "Food Science and Nutrition"),
        "food/agr": ("College of Food, Agricultural and Natural Resource Sciences", "Food Science and Nutrition"),
        "agricultural": ("College of Food, Agricultural and Natural Resource Sciences", "Applied Economics"),
        "agronomy": ("College of Food, Agricultural and Natural Resource Sciences", "Plant and Soil Sciences"),
        "forest": ("College of Food, Agricultural and Natural Resource Sciences", "Forest Resources"),
        "veterinary": ("College of Food, Agricultural and Natural Resource Sciences", "Veterinary Clinical Sciences"),
        "cfans": ("College of Food, Agricultural and Natural Resource Sciences", "Other"),
        
        # CLA
        "lib arts": ("College of Liberal Arts", "Other"),
        "cla": ("College of Liberal Arts", "Other"),
        "art ": ("College of Liberal Arts", "Art"),
        "music": ("College of Liberal Arts", "Music"),
        "english": ("College of Liberal Arts", "English"),
        "history": ("College of Liberal Arts", "History"),
        "sociology": ("College of Liberal Arts", "Sociology"),
        "philosophy": ("College of Liberal Arts", "Philosophy"),
        "anthropology": ("College of Liberal Arts", "Anthropology"),
        "psychology": ("College of Liberal Arts", "Psychology"),
        "political science": ("College of Liberal Arts", "Political Science"),
        "economics": ("College of Liberal Arts", "Economics"),
        "communication": ("College of Liberal Arts", "Communication Studies"),
        "theatre": ("College of Liberal Arts", "Theatre Arts and Dance"),
        "dance": ("College of Liberal Arts", "Theatre Arts and Dance"),
        "linguistics": ("College of Liberal Arts", "Linguistics"),
        "german": ("College of Liberal Arts", "German, Scandinavian and Dutch"),
        "scandinavian": ("College of Liberal Arts", "Scandinavian Studies"),
        "french": ("College of Liberal Arts", "French and Italian"),
        "italian": ("College of Liberal Arts", "French and Italian"),
        "spanish": ("College of Liberal Arts", "Spanish and Portuguese"),
        "portuguese": ("College of Liberal Arts", "Spanish and Portuguese"),
        "asian": ("College of Liberal Arts", "Asian Languages and Literatures"),
        "classics": ("College of Liberal Arts", "Classics"),
        "religious": ("College of Liberal Arts", "Religious Studies"),
        
        # CSE
        "biomedical eng": ("College of Science and Engineering", "Biomedical Engineering"),
        "cseng chemical": ("College of Science and Engineering", "Chemical Engineering and Materials Science"),
        "cseng chemistry": ("College of Science and Engineering", "Chemistry"),
        "chemistry admin": ("College of Science and Engineering", "Chemistry"),
        "cseng civil": ("College of Science and Engineering", "Civil, Environmental and Geo-Engineering"),
        "cseng mech": ("College of Science and Engineering", "Mechanical Engineering"),
        "mechanical eng": ("College of Science and Engineering", "Mechanical Engineering"),
        "computer science": ("College of Science and Engineering", "Computer Science and Engineering"),
        "cseng aerospace": ("College of Science and Engineering", "Aerospace Engineering and Mechanics"),
        "industrial system": ("College of Science and Engineering", "Industrial and Systems Engineering"),
        "geology": ("College of Science and Engineering", "Geological Sciences"),
        "physics": ("College of Science and Engineering", "Physics"),
        "mathematics": ("College of Science and Engineering", "Mathematics"),
        "cseng": ("College of Science and Engineering", "Other"),
        "science/eng": ("College of Science and Engineering", "Other"),
        "statistics": ("College of Science and Engineering", "Mathematics"),
        "bio science": ("College of Science and Engineering", "Physics"),
        "cbs": ("College of Science and Engineering", "Physics"),
        "medicinal chemistry": ("College of Science and Engineering", "Chemistry"),
        
        # Carlson
        "carlson": ("Carlson School of Management", "Business and Management"),
        "management": ("Carlson School of Management", "Business and Management"),
        "accounting": ("Carlson School of Management", "Accounting"),
        "finance": ("Carlson School of Management", "Finance"),
        "bus/econ": ("Carlson School of Management", "Business and Management"),
        
        # Medical School
        "medicine": ("Medical School", "Medicine"),
        "med sch": ("Medical School", "Medicine"),
        "anesthesiology": ("Medical School", "Anesthesiology"),
        "anes": ("Medical School", "Anesthesiology"),
        "dermatology": ("Medical School", "Dermatology"),
        "neurology": ("Medical School", "Neurology"),
        "neuroscience": ("Medical School", "Neuroscience"),
        "oncology": ("Medical School", "Oncology"),
        "pediatrics": ("Medical School", "Pediatrics"),
        "peds": ("Medical School", "Pediatrics"),
        "psychiatry": ("Medical School", "Psychiatry"),
        "radiology": ("Medical School", "Radiology"),
        "surgery": ("Medical School", "Surgery"),
        "internal medicine": ("Medical School", "General Internal Medicine"),
        "med cardiology": ("Medical School", "General Internal Medicine"),
        "obstetrics": ("Medical School", "Obstetrics, Gynecology and Reproductive Medicine"),
        "ob/gyn": ("Medical School", "Obstetrics, Gynecology and Reproductive Medicine"),
        "orthop": ("Medical School", "Orthopaedic Surgery"),
        "otolaryngology": ("Medical School", "Otolaryngology"),
        "urology": ("Medical School", "Urology"),
        "ophthalmology": ("Medical School", "Ophthalmology"),
        "pharmacology": ("Medical School", "Pharmacology"),
        "pathology": ("Medical School", "Pathology"),
        "microbiology": ("Medical School", "Microbiology and Immunology"),
        "immunology": ("Medical School", "Immunology"),
        "biochemistry": ("Medical School", "Biochemistry, Molecular Biology and Biophysics"),
        "bmbb": ("Medical School", "Biochemistry, Molecular Biology and Biophysics"),
        "genetics": ("Medical School", "Genetics, Cell Biology and Development"),
        "physiology": ("Medical School", "Physiology"),
        "fammed": ("Medical School", "Family Medicine and Community Health"),
        "family medicine": ("Medical School", "Family Medicine and Community Health"),
        "dmed": ("Medical School", "Family Medicine and Community Health"),
        "emergency": ("Medical School", "Emergency Medicine"),
        "dent biomaterials": ("Medical School", "Biomaterials"),
        "dent molecular": ("Medical School", "Microbiology and Immunology"),
        "experimental clinical pharm": ("Medical School", "Pharmacology"),
        "health informatics": ("Medical School", "Medicine"),
        
        # Dentistry
        "dent basic": ("School of Dentistry", "Oral Biology and Diagnostic Sciences"),
        "dent periodontics": ("School of Dentistry", "Periodontics, Prosthodontics and Implant Dentistry"),
        "endodontics": ("School of Dentistry", "Endodontics"),
        "oral surgery": ("School of Dentistry", "Oral and Maxillofacial Surgery"),
        "lmp": ("School of Dentistry", "Oral and Maxillofacial Pathology"),
        "gcd": ("School of Dentistry", "Oral Biology and Diagnostic Sciences"),
        "dent": ("School of Dentistry", "Oral Biology and Diagnostic Sciences"),
        "dentistry": ("School of Dentistry", "Oral Biology and Diagnostic Sciences"),
        
        # Nursing
        "nursing": ("School of Nursing", "Nursing"),
        "son": ("School of Nursing", "Nursing"),
        
        # Public Health
        "sph": ("School of Public Health", "Division of Epidemiology and Community Health"),
        "public hlth": ("School of Public Health", "Division of Epidemiology and Community Health"),
        "epidemiology": ("School of Public Health", "Division of Epidemiology and Community Health"),
        "biostatistics": ("School of Public Health", "Biostatistics"),
        "environmental health": ("School of Public Health", "Division of Environmental Health Sciences"),
        "health policy": ("School of Public Health", "Division of Health Policy and Management"),
        
        # Pharmacy
        "pharmacy": ("School of Pharmacy", "Pharmacy"),
        "cop": ("School of Pharmacy", "Pharmacy"),
        
        # Architecture
        "architecture": ("School of Architecture", "Architecture"),
        "design": ("School of Architecture", "Architecture"),
        
        # Other Colleges
        "kinesiology": ("College of Liberal Arts", "Psychology"),
        "ed psych": ("College of Liberal Arts", "Psychology"),
        "cehd": ("College of Liberal Arts", "Education"),
        "educ/hum": ("College of Liberal Arts", "Education"),
        "speech-language": ("College of Liberal Arts", "Communication Studies"),
        "physical therapy": ("College of Liberal Arts", "Psychology"),
        "grad school": ("Graduate School", "Graduate Studies"),
        "law school": ("Law School", "Law"),
    }
    
    # Try to match patterns
    for pattern, (school, dept) in dept_patterns.items():
        if pattern in dept_lower:
            return school, dept
    
    # Default fallback
    return None, dept_str

if __name__ == "__main__":
    # Print structure for reference
    import json
    print(json.dumps(UMN_STRUCTURE, indent=2))
