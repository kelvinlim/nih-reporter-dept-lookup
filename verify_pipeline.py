import json
import pandas as pd
from fetch_grants import fetch_grants
from fetch_pi_details import get_pi_details
import time

def verify():
    print("--- Running Verification Pipeline (Sample 5 records) ---")
    
    # 1. Fetch Grants (Just 1 year to start, and limit to 5 records manually)
    print("\n[Step 1] Fetching sample grants...")
    # We fetch 2024, but we'll slice strictly.
    # Note: fetch_grants gets all for a year, but we can just use the first few.
    # To avoid waiting for ALL of 2024, we can trust fetch_grants works (based on logs) 
    # but strictly speaking verify fetch_grants needs to return *some* data quickly.
    # We can modify fetch logic to be faster or just let it run for one year's first page.
    
    # Actually, we can just instantiate the loop and break early, or use correct logic.
    # For now, let's just use the fetch_grants as is but with a fake 'years' param if we could, 
    # but simpler is to just import logic or copy-paste for test.
    # Or better: let's modifying fetch_grants to accept a 'limit_total' param? 
    # No, let's just run it for the current year (which has few records usually) or 2026.
    
    projects = fetch_grants(years=[2025]) # 2025 has ~856 records. active.
    # We'll just take the top 5.
    projects = projects[:5]
    print(f"  Selected {len(projects)} projects for verification.")

    # 2. Enrich
    print("\n[Step 2] Enriching...")
    enriched = []
    for p in projects:
        pi_name = p.get("contact_pi_name")
        print(f"  Processing {pi_name}...")
        
        details = get_pi_details(pi_name)
        
        p["pi_rank"] = details.get("rank") if details else None
        p["pi_department"] = details.get("department") if details else None
        p["pi_school"] = details.get("organization") if details else None
        
        enriched.append(p)
        time.sleep(0.5)

    # 3. Save
    print("\n[Step 3] Saving...")
    with open("verify_pipeline_output.json", "w") as f:
        json.dump(enriched, f, indent=2)
        
    df = pd.json_normalize(enriched)
    print("  Results sample:")
    print(df[["project_num", "contact_pi_name", "pi_department", "pi_rank"]].to_string())
    
    print("\nVerification Complete.")

if __name__ == "__main__":
    verify()
