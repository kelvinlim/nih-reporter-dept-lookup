import requests
import json
import datetime
import time

API_URL = "https://api.reporter.nih.gov/v2/projects/search"

def get_fiscal_years(num_years=5):
    current_year = datetime.datetime.now().year
    if num_years == 0:
        return [current_year]
    return [current_year - i for i in range(num_years)]

def fetch_va_grants(years=None, org_name=None):
    """
    Fetch VA-funded grants from NIH RePORTER API v2.

    Args:
        years: int (number of years) or list of fiscal years. Default 5.
        org_name: Optional organization name filter (e.g. "MINNEAPOLIS VA MEDICAL CENTER").
                  If None, fetches ALL VA grants.

    Returns:
        list of project dicts
    """
    if years is None:
        years = get_fiscal_years(5)
    elif isinstance(years, int):
        years = get_fiscal_years(years)

    all_projects = []

    for year in years:
        print(f"Fetching VA grants for FY {year}...")

        criteria = {
            "fiscal_years": [year],
            "agencies": ["VA"]
        }
        if org_name:
            criteria["org_names"] = [org_name]

        payload = {
            "criteria": criteria,
            "include_fields": [
                "ProjectNum",
                "ProjectTitle",
                "ContactPiName",
                "PrincipalInvestigators",
                "FiscalYear",
                "AwardAmount",
                "ProjectStartDate",
                "ProjectEndDate",
                "BudgetStart",
                "BudgetEnd",
                "AbstractText",
                "Organization",
                "CongDist"
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

                total = data.get("meta", {}).get("total", "Unknown")
                print(f"  Retrieved {len(results)} records (offset {payload['offset']}). Total for FY {year}: {total}")

                if len(results) < payload["limit"]:
                    break

                payload["offset"] += payload["limit"]
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                print(f"Error fetching data for FY {year}: {e}")
                break

    return all_projects

if __name__ == "__main__":
    projects = fetch_va_grants(years=1)
    print(f"Total VA projects retrieved: {len(projects)}")

    if projects:
        with open("va_grants_sample.json", "w") as f:
            json.dump(projects[:5], f, indent=2)
        print("Saved sample to va_grants_sample.json")
