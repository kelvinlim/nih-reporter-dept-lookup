import requests
import json
import datetime
import time

API_URL = "https://api.reporter.nih.gov/v2/projects/search"

def get_fiscal_years(num_years=10):
    current_year = datetime.datetime.now().year
    if num_years == 0:
        return [current_year]
    return [current_year - i for i in range(num_years)]

def fetch_grants(org_name="UNIVERSITY OF MINNESOTA", years=None):
    if years is None:
        # Default behavior if not specified, though main.py will likely pass a list or int
        years = get_fiscal_years(10)
    elif isinstance(years, int):
        years = get_fiscal_years(years)
    
    all_projects = []
    
    for year in years:
        print(f"Fetching grants for FY {year}...")
        payload = {
            "criteria": {
                "fiscal_years": [year],
                "org_names": [org_name]
            },
            "include_fields": [
                "ProjectNum",
                "ProjectTitle",
                "ContactPiName",
                "FiscalYear",
                "AwardAmount",
                "ProjectStartDate",
                "ProjectEndDate",
                "BudgetStart",
                "BudgetEnd",
                "AbstractText"
            ],
            "offset": 0,
            "limit": 500,
            "sort_field": "project_start_date",
            "sort_order": "desc"
        }
        
        while True:
            try:
                response = requests.post(API_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                all_projects.extend(results)
                
                print(f"  Retrieved {len(results)} records. Total for FY {year}: {data.get('meta', {}).get('total', 'Unknown')}")
                
                if len(results) < payload["limit"]:
                    break
                
                payload["offset"] += payload["limit"]
                time.sleep(1) # Be nice to the API
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching data for FY {year}: {e}")
                break
                
    return all_projects

if __name__ == "__main__":
    projects = fetch_grants()
    print(f"Total projects retrieved: {len(projects)}")
    
    # Save a sample to check structure
    if projects:
        with open("grants_sample.json", "w") as f:
            json.dump(projects[:5], f, indent=2)
        print("Saved sample to grants_sample.json")
