import requests
import urllib.parse
import time

ORCID_API_BASE = "https://pub.orcid.org/v3.0"

def get_pi_details(contact_pi_name, org_name="University of Minnesota"):
    """
    Retrieves PI details (Rank, Department, School) from ORCID.
    """
    print(f"Looking up details for: {contact_pi_name}")
    
    # parse name (Assuming "Last, First" or "Last, First M")
    try:
        if "," in contact_pi_name:
            parts = contact_pi_name.split(",")
            last_name = parts[0].strip()
            first_name = parts[1].strip().split(" ")[0] # Take first part of first name
        else:
            # Fallback for "First Last"
            parts = contact_pi_name.split(" ")
            last_name = parts[-1]
            first_name = parts[0]
    except Exception as e:
        print(f"  Error parsing name {contact_pi_name}: {e}")
        return None

    # Search for person
    query = f"family-name:{last_name} AND given-names:{first_name} AND affiliation-org-name:({urllib.parse.quote(org_name)})"
    search_url = f"{ORCID_API_BASE}/search/?q={query}"
    headers = {"Accept": "application/json"}
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        num_found = data.get("num-found", 0)
        
        if num_found == 0:
            print(f"  No ORCID record found for {contact_pi_name} at {org_name}")
            return None
        
        print(f"  Found {num_found} ORCID record(s). Checking employments...")
        
        results = data.get("result", [])
        for result in results:
            orcid_id = result.get("orcid-identifier", {}).get("path")
            if not orcid_id:
                continue
                
            # Fetch employments
            details = get_employment_details(orcid_id, org_name)
            if details:
                print(f"  Match found: {details}")
                return details
                
            time.sleep(0.5) # Rate limit courtesy
            
    except requests.exceptions.RequestException as e:
        print(f"  ORCID API Request Error: {e}")
        return None
        
    print(f"  No matching current employment found for {contact_pi_name}")
    return None

def get_employment_details(orcid_id, target_org_name):
    url = f"{ORCID_API_BASE}/{orcid_id}/employments"
    headers = {"Accept": "application/json"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        data = response.json()
        affiliation_groups = data.get("affiliation-group", [])
        
        for group in affiliation_groups:
            summaries = group.get("summaries", [])
            for summary in summaries:
                emp_summary = summary.get("employment-summary", {})
                
                # Check for active employment (end-date is null)
                end_date = emp_summary.get("end-date")
                if end_date is not None:
                    continue
                    
                org = emp_summary.get("organization", {})
                org_name = org.get("name", "")
                
                # Loose matching for organization
                if target_org_name.lower() in org_name.lower():
                    return {
                        "orcid_id": orcid_id,
                        "rank": emp_summary.get("role-title"),
                        "department": emp_summary.get("department-name"),
                        "organization": org_name,
                        "source": "ORCID"
                    }
                    
    except Exception as e:
        print(f"  Error fetching employments for {orcid_id}: {e}")
        
    return None

if __name__ == "__main__":
    # Test with known PI
    details = get_pi_details("LIM, KELVIN", "University of Minnesota")
    print(f"Result: {details}")
