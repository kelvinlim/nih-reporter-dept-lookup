import argparse
import json
import os
import time
import datetime
import pandas as pd
from fetch_va_grants import fetch_va_grants
from scrape_va_details import build_listing_index, scrape_detail_page

# File Constants
FILE_RAW = "va_projects_raw.json"
FILE_BY_PI = "va_projects_by_pi.json"
FILE_VA_DETAILS = "va_project_details.json"
FILE_FINAL = "va_final_data.json"
FILE_FINAL_CSV = "va_final_data.csv"
FILE_RUNWAY = "va_runway_import.json"


def extract_core_project_num(project_num):
    """
    Extracts core project number from full string.
    Example: 'IK2RX004298-01A1' -> 'IK2RX004298'
             '1I01BX006000-01A1' -> 'I01BX006000'
    """
    if not project_num:
        return "Unknown"
    base = project_num.split("-")[0]
    if base and base[0].isdigit():
        return base[1:]
    return base


def _make_placeholder_email(pi_name, email_set):
    """
    Generate a name-based placeholder email from PI name.
    Format: firstname.lastname@va.placeholder
    Handles duplicates by appending a number.
    """
    parts = pi_name.split(", ", 1)
    last = parts[0].strip().lower() if parts else pi_name.strip().lower()
    first_raw = parts[1].strip().lower() if len(parts) > 1 else ""
    # Take only first name (drop middle)
    first = first_raw.split()[0] if first_raw.split() else "unknown"

    # Clean: keep only alphanumeric and dots
    import re
    first = re.sub(r'[^a-z0-9]', '', first)
    last = re.sub(r'[^a-z0-9]', '', last)

    base_email = f"{first}.{last}@va.placeholder"
    email = base_email
    counter = 2
    while email in email_set:
        email = f"{first}.{last}.{counter}@va.placeholder"
        counter += 1
    return email


def _get_profile_id_for_pi(pi_name, projects_by_pi):
    """Extract NIH profile_id for a contact PI from their project data."""
    core_groups = projects_by_pi.get(pi_name, {})
    for core_num, proj_list in core_groups.items():
        for proj in proj_list:
            for pi_entry in proj.get("principal_investigators") or []:
                if pi_entry.get("is_contact_pi"):
                    pid = pi_entry.get("profile_id")
                    if pid:
                        return str(pid)
    return None


def _get_copi_profile_id(copi_name, proj):
    """Extract NIH profile_id for a co-PI from a project's principal_investigators."""
    for pi_entry in proj.get("principal_investigators") or []:
        last = pi_entry.get("last_name", "").strip().upper()
        first = pi_entry.get("first_name", "").strip().upper()
        middle = pi_entry.get("middle_name", "").strip().upper()
        name = f"{last}, {first} {middle}".strip() if first else last
        if name == copi_name:
            pid = pi_entry.get("profile_id")
            return str(pid) if pid else None
    return None


# ── Step 1: Fetch VA grants ──────────────────────────────────────────────────

def step_projects(years=5, org_name=None):
    """Fetch VA grants from NIH RePORTER API and save to FILE_RAW."""
    print(f"--- [Step 1] Fetching VA Projects ---")
    if years == 0:
        print("Fetching projects for the current year only.")
    else:
        print(f"Fetching projects for the last {years} years.")
    if org_name:
        print(f"Filtering by organization: {org_name}")

    projects = fetch_va_grants(years=years, org_name=org_name)
    print(f"Total VA projects fetched: {len(projects)}")

    with open(FILE_RAW, "w") as f:
        json.dump(projects, f, indent=2)
    print(f"Saved raw data to {FILE_RAW}")


# ── Step 2: Reorganize by PI ─────────────────────────────────────────────────

def step_reorganize():
    """Reorganize raw data by PI, then Core Grant Number."""
    print(f"--- [Step 2] Reorganizing Data ---")
    if not os.path.exists(FILE_RAW):
        print(f"Error: {FILE_RAW} not found. Run --projects first.")
        return

    with open(FILE_RAW, "r") as f:
        raw_projects = json.load(f)

    projects_by_pi = {}
    print(f"Processing {len(raw_projects)} records...")

    for project in raw_projects:
        pi_name = project.get("contact_pi_name")
        if not pi_name:
            pi_name = "Unknown"

        proj_num = project.get("project_num")
        core_num = extract_core_project_num(proj_num)
        project["core_project_num"] = core_num

        # Create project_num_clip (remove leading digit if present)
        if proj_num and len(proj_num) > 0 and proj_num[0].isdigit():
            clip = proj_num[1:]
        else:
            clip = proj_num

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


# ── Step 3: Scrape VA website ────────────────────────────────────────────────

def step_scrape(years=5, skip_details=False):
    """Scrape VA website for supplemental project details (total award, location, service)."""
    print(f"--- [Step 3] Scraping VA Website ---")
    if not os.path.exists(FILE_BY_PI):
        print(f"Error: {FILE_BY_PI} not found. Run --reorganize first.")
        return

    with open(FILE_BY_PI, "r") as f:
        projects_by_pi = json.load(f)

    # Collect all unique project numbers from API data
    api_project_nums = set()
    for pi_name, core_groups in projects_by_pi.items():
        for core_num, proj_list in core_groups.items():
            for proj in proj_list:
                pnum = proj.get("project_num")
                if pnum:
                    api_project_nums.add(pnum)
    print(f"Found {len(api_project_nums)} unique project numbers from API data")

    # Load existing cache
    va_details = {}
    if os.path.exists(FILE_VA_DETAILS):
        print(f"Found existing {FILE_VA_DETAILS}, loading cache...")
        with open(FILE_VA_DETAILS, "r") as f:
            va_details = json.load(f)

    # Build year list
    current_year = datetime.datetime.now().year
    if isinstance(years, int):
        year_list = [current_year - i for i in range(years)] if years > 0 else [current_year]
    else:
        year_list = years

    # Phase 1: Scrape listing pages to build project_num -> pid index
    print(f"\nPhase 1: Scraping listing pages for FY {year_list}...")
    listing_index = build_listing_index(year_list)
    print(f"Built index of {len(listing_index)} projects from VA website listings")

    # Build core-number index from listing (strip suffix and leading digit)
    listing_core_index = {}
    for pn, entry in listing_index.items():
        core = extract_core_project_num(pn)
        if core != "Unknown" and core not in listing_core_index:
            listing_core_index[core] = entry

    # Match API project numbers to listing index
    # Try: raw match, clipped match (no leading digit), then core number match
    matched = {}
    for proj_num in api_project_nums:
        if proj_num in listing_index:
            matched[proj_num] = listing_index[proj_num]
        else:
            clip = proj_num[1:] if proj_num and proj_num[0].isdigit() else proj_num
            if clip in listing_index:
                matched[proj_num] = listing_index[clip]
            else:
                # Fall back to core project number match
                core = extract_core_project_num(proj_num)
                if core in listing_core_index:
                    matched[proj_num] = listing_core_index[core]

    unmatched_count = len(api_project_nums) - len(matched)
    print(f"Matched {len(matched)} of {len(api_project_nums)} API projects to VA website listings")
    if unmatched_count:
        print(f"  ({unmatched_count} projects not found on VA website)")

    if skip_details:
        # Save listing data only
        for proj_num, entry in matched.items():
            if proj_num not in va_details:
                va_details[proj_num] = {
                    "pid": entry["pid"],
                    "listing_column_name": entry["listing_column_name"],
                    "listing_column_value": entry["listing_column_value"],
                }
        with open(FILE_VA_DETAILS, "w") as f:
            json.dump(va_details, f, indent=2)
        print(f"Saved listing data to {FILE_VA_DETAILS} (detail scraping skipped)")
        return

    # Phase 2: Scrape detail pages for total_award_amount etc.
    # Re-scrape entries that exist in cache but are missing detail data (e.g., from --skip-details)
    to_scrape = {pn: entry for pn, entry in matched.items()
                 if pn not in va_details
                 or va_details[pn].get("total_award_amount") is None
                 or (va_details[pn].get("portfolio") is None and va_details[pn].get("research_service") is None)}
    print(f"\nPhase 2: Scraping {len(to_scrape)} detail pages...")

    count = 0
    for proj_num, entry in to_scrape.items():
        count += 1
        pid = entry["pid"]
        fy = entry["fiscal_year"]

        print(f"  [{count}/{len(to_scrape)}] {proj_num} (pid={pid})")

        detail = scrape_detail_page(fy, pid)

        va_details[proj_num] = {
            "pid": pid,
            "listing_column_name": entry["listing_column_name"],
            "listing_column_value": entry["listing_column_value"],
        }
        if detail:
            va_details[proj_num].update(detail)

        # Checkpoint every 10 records
        if count % 10 == 0:
            with open(FILE_VA_DETAILS, "w") as f:
                json.dump(va_details, f, indent=2)
            print(f"    (Checkpoint: saved {count} records)")

        time.sleep(1)

    with open(FILE_VA_DETAILS, "w") as f:
        json.dump(va_details, f, indent=2)
    print(f"Saved {len(va_details)} project details to {FILE_VA_DETAILS}")


# ── Step 4: Join ─────────────────────────────────────────────────────────────

def step_join():
    """Join API data with scraped VA details into final output."""
    print(f"--- [Step 4] Joining Data ---")
    if not os.path.exists(FILE_BY_PI):
        print(f"Error: {FILE_BY_PI} not found. Run --reorganize first.")
        return

    with open(FILE_BY_PI, "r") as f:
        projects_by_pi = json.load(f)

    # VA details are optional
    va_details = {}
    if os.path.exists(FILE_VA_DETAILS):
        with open(FILE_VA_DETAILS, "r") as f:
            va_details = json.load(f)
        print(f"Loaded {len(va_details)} scraped detail records")
    else:
        print(f"Warning: {FILE_VA_DETAILS} not found. Proceeding without scraped data.")

    final_data = []
    matched_count = 0

    for pi_name, core_groups in projects_by_pi.items():
        for core_num, projects in core_groups.items():
            for project in projects:
                enriched = project.copy()

                # Extract PI title and profile_id from principal_investigators
                pis = project.get("principal_investigators") or []
                for pi_entry in pis:
                    if pi_entry.get("is_contact_pi"):
                        enriched["pi_title"] = pi_entry.get("title")
                        enriched["pi_profile_id"] = pi_entry.get("profile_id")
                        break

                # Merge scraped details
                proj_num = project.get("project_num")
                if proj_num and proj_num in va_details:
                    detail = va_details[proj_num]
                    enriched["total_award_amount"] = detail.get("total_award_amount")
                    enriched["project_period"] = detail.get("project_period")
                    enriched["va_location"] = detail.get("location")
                    enriched["congressional_district"] = detail.get("congressional_district")
                    enriched["portfolio"] = detail.get("portfolio")
                    enriched["research_service"] = detail.get("research_service")
                    matched_count += 1

                final_data.append(enriched)

    with open(FILE_FINAL, "w") as f:
        json.dump(final_data, f, indent=2)
    print(f"Saved final JSON to {FILE_FINAL}")
    print(f"  Total records: {len(final_data)}, with scraped details: {matched_count}")

    try:
        df = pd.json_normalize(final_data)
        # Drop nested columns that don't flatten well in CSV
        for col in ["principal_investigators"]:
            if col in df.columns:
                df = df.drop(columns=[col])
        df.to_csv(FILE_FINAL_CSV, index=False)
        print(f"Saved final CSV to {FILE_FINAL_CSV}")
    except Exception as e:
        print(f"Error saving CSV: {e}")


# ── Step 5: Pack for Runway ──────────────────────────────────────────────────

def step_pack():
    """Pack into Runway bulk import v1.0 format."""
    print(f"--- [Step 5] Packing for Runway Import (v1.0) ---")
    if not os.path.exists(FILE_BY_PI):
        print(f"Error: {FILE_BY_PI} not found. Run --reorganize first.")
        return

    with open(FILE_BY_PI, "r") as f:
        projects_by_pi = json.load(f)

    # Load scraped details if available (for location, total award, etc.)
    va_details = {}
    if os.path.exists(FILE_VA_DETAILS):
        with open(FILE_VA_DETAILS, "r") as f:
            va_details = json.load(f)

    # 1. Hierarchy
    hierarchy_levels = ["Organization", "Site", "Unit"]

    # 2. Schemas
    schemas = {
        "user": {
            "general": {
                "_section": {"label": "General", "color": "blue"},
                "rank": {"type": "string", "title": "Academic Rank"},
                "nih_investigator_id": {"type": "string", "title": "NIH Investigator ID"},
                "is_investigator": {"type": "boolean", "title": "Investigator"}
            }
        },
        "project": {
            "grant_info": {
                "_section": {"label": "Grant Information", "color": "green"},
                "award_number": {"type": "string", "title": "Award Number"},
                "core_project_num": {"type": "string", "title": "Core Project Number"},
                "award_amount": {"type": "number", "title": "Award Amount (FY)"},
                "total_award_amount": {"type": "number", "title": "Total Award Amount"},
                "funding_agency": {"type": "string", "title": "Funding Agency"},
                "portfolio": {"type": "string", "title": "Portfolio"},
                "research_service": {"type": "string", "title": "Research Service"},
                "project_start_date": {"type": "string", "format": "date", "title": "Start Date"},
                "project_end_date": {"type": "string", "format": "date", "title": "End Date"},
                "budget_start": {"type": "string", "format": "date", "title": "Budget Start"},
                "budget_end": {"type": "string", "format": "date", "title": "Budget End"}
            }
        }
    }

    # 3. Build users, projects, and discover sites
    users = []
    projects = []
    email_set = set()
    sites = set()
    # Map PI name -> email for co-PI lookups
    pi_email_map = {}
    # Map PI name -> profile_id
    pi_profile_map = {}

    for pi_name, core_groups in projects_by_pi.items():
        if pi_name == "Unknown":
            continue

        # Determine site from org_city/org_state (from first project)
        first_proj = None
        for core_num, proj_list in core_groups.items():
            if proj_list:
                first_proj = proj_list[0]
                break
        if not first_proj:
            continue

        org = first_proj.get("organization") or {}
        org_city = (org.get("org_city") or "").strip()
        org_state = (org.get("org_state") or "").strip()
        # Title-case the city but keep state abbreviation uppercase
        city_display = org_city.title() if org_city == org_city.upper() else org_city
        site = f"{city_display}, {org_state}" if city_display and org_state else city_display or org_state or "Unknown Site"
        sites.add(site)

        # Parse name
        parts = pi_name.split(", ", 1)
        last_name = parts[0].strip().title() if parts else pi_name.title()
        first_name = parts[1].strip().title() if len(parts) > 1 else ""
        first_name_parts = first_name.split()
        first_name = first_name_parts[0] if first_name_parts else first_name

        # Generate placeholder email
        email = _make_placeholder_email(pi_name, email_set)
        email_set.add(email)
        pi_email_map[pi_name] = email

        # Get profile_id
        profile_id = _get_profile_id_for_pi(pi_name, projects_by_pi)
        if profile_id:
            pi_profile_map[pi_name] = profile_id

        unit_path = ["Department of Veterans Affairs", site]

        # Get rank from principal_investigators
        rank = None
        for core_num, proj_list in core_groups.items():
            for proj in proj_list:
                for pi_entry in proj.get("principal_investigators") or []:
                    if pi_entry.get("is_contact_pi") and pi_entry.get("title"):
                        rank = pi_entry["title"]
                        break
                if rank:
                    break
            if rank:
                break

        user_entry = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "unit_path": unit_path,
            "is_investigator": True,
            "attributes": {}
        }
        if rank:
            user_entry["attributes"]["general.rank"] = rank
        if profile_id:
            user_entry["attributes"]["general.nih_investigator_id"] = profile_id
        users.append(user_entry)

        # Add projects - take most recent fiscal year record per core grant
        for core_num, proj_list in core_groups.items():
            proj_list_sorted = sorted(proj_list, key=lambda p: p.get("fiscal_year", 0), reverse=True)
            proj = proj_list_sorted[0]

            title = proj.get("project_title") or proj.get("title") or f"Grant {core_num}"

            # Format dates
            start = (proj.get("project_start_date") or "")[:10]
            end = (proj.get("project_end_date") or "")[:10]
            budget_start = (proj.get("budget_start") or "")[:10]
            budget_end = (proj.get("budget_end") or "")[:10]

            abstract = (proj.get("abstract_text") or "").strip()

            # Build co-PI list
            co_pis = []
            for pi_entry in proj.get("principal_investigators") or []:
                if pi_entry.get("is_contact_pi"):
                    continue
                copi_last = pi_entry.get("last_name", "").strip().upper()
                copi_first_raw = pi_entry.get("first_name", "").strip().upper()
                copi_middle = pi_entry.get("middle_name", "").strip().upper()
                if not copi_last:
                    continue
                copi_name = f"{copi_last}, {copi_first_raw} {copi_middle}".strip() if copi_first_raw else copi_last

                # Look up or create email for co-PI
                if copi_name in pi_email_map:
                    copi_email = pi_email_map[copi_name]
                else:
                    copi_email = _make_placeholder_email(copi_name, email_set)
                    email_set.add(copi_email)
                    pi_email_map[copi_name] = copi_email

                    # Add co-PI as user
                    copi_parts = copi_name.split(", ", 1)
                    copi_last_title = copi_parts[0].strip().title() if copi_parts else copi_name.title()
                    copi_first_title = copi_parts[1].strip().title() if len(copi_parts) > 1 else ""
                    copi_first_title = copi_first_title.split()[0] if copi_first_title.split() else copi_first_title

                    # Co-PI might be at a different site; use project's site as default
                    copi_profile_id = _get_copi_profile_id(copi_name, proj)
                    copi_user = {
                        "email": copi_email,
                        "first_name": copi_first_title,
                        "last_name": copi_last_title,
                        "unit_path": unit_path,  # Same site as the project
                        "is_investigator": True,
                        "attributes": {}
                    }
                    copi_rank = pi_entry.get("title")
                    if copi_rank:
                        copi_user["attributes"]["general.rank"] = copi_rank
                    if copi_profile_id:
                        copi_user["attributes"]["general.nih_investigator_id"] = copi_profile_id
                    users.append(copi_user)

                co_pis.append(copi_email)

            # Merge scraped details
            proj_num = proj.get("project_num")
            scraped = va_details.get(proj_num, {}) if proj_num else {}

            project_entry = {
                "title": title,
                "pi_email": email,
                "pi_name": pi_name,
                "status": "current",
                "unit_path": unit_path,
                "attributes": {
                    "grant_info.award_number": proj.get("project_num", ""),
                    "grant_info.core_project_num": core_num,
                    "grant_info.award_amount": proj.get("award_amount"),
                    "grant_info.funding_agency": "VA",
                }
            }
            # Total award from scraping
            total_award = scraped.get("total_award_amount")
            if total_award:
                project_entry["attributes"]["grant_info.total_award_amount"] = total_award
            # Portfolio / Research service
            portfolio = scraped.get("portfolio")
            if portfolio:
                project_entry["attributes"]["grant_info.portfolio"] = portfolio
            research_svc = scraped.get("research_service")
            if research_svc:
                project_entry["attributes"]["grant_info.research_service"] = research_svc

            if co_pis:
                project_entry["co_pis"] = co_pis
            if abstract:
                project_entry["abstract"] = abstract
            if start:
                project_entry["attributes"]["grant_info.project_start_date"] = start
            if end:
                project_entry["attributes"]["grant_info.project_end_date"] = end
            if budget_start:
                project_entry["attributes"]["grant_info.budget_start"] = budget_start
            if budget_end:
                project_entry["attributes"]["grant_info.budget_end"] = budget_end

            projects.append(project_entry)

    # 4. Build unit tree
    unit_tree = {
        "name": "Department of Veterans Affairs",
        "children": [{"name": s, "children": []} for s in sorted(sites)]
    }

    # 5. Assemble final import file
    from datetime import date
    runway_data = {
        "metadata": {
            "version": "1.0",
            "description": "VA-funded researchers and grants",
            "created": str(date.today()),
            "source": "va-grant-pipeline (NIH RePORTER API + VA website)",
            "effort_defaults": {
                "create_effort": True,
                "default_person_months": 3.0,
                "period_type": "calendar"
            }
        },
        "hierarchy_levels": hierarchy_levels,
        "units": unit_tree,
        "schemas": schemas,
        "users": users,
        "projects": projects,
    }

    with open(FILE_RUNWAY, "w") as f:
        json.dump(runway_data, f, indent=2)
    print(f"Saved Runway import file to {FILE_RUNWAY}")

    # Summary
    print(f"\nSummary:")
    print(f"  Hierarchy: {' -> '.join(hierarchy_levels)}")
    print(f"  Sites: {len(sites)}")
    print(f"  Users: {len(users)} investigators")
    print(f"  Projects: {len(projects)} grants (most recent per core number)")
    print(f"  Schemas: user ({len(schemas['user'])} categories), project ({len(schemas['project'])} categories)")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="VA Grant Data Pipeline")
    parser.add_argument("--projects", action="store_true", help="Fetch VA grants from NIH RePORTER")
    parser.add_argument("--years", type=int, default=5, help="Number of years to fetch (default 5)")
    parser.add_argument("--org", type=str, default=None, help="Filter by organization name (e.g. 'MINNEAPOLIS VA MEDICAL CENTER')")
    parser.add_argument("--reorganize", action="store_true", help="Organize grants by PI")
    parser.add_argument("--scrape", action="store_true", help="Scrape VA website for supplemental details")
    parser.add_argument("--skip-details", action="store_true", help="Skip detail page scraping (listing data only)")
    parser.add_argument("--join", action="store_true", help="Join API data with scraped details")
    parser.add_argument("--pack", action="store_true", help="Pack for Runway import")

    args = parser.parse_args()

    if args.projects:
        step_projects(years=args.years, org_name=args.org)

    if args.reorganize:
        step_reorganize()

    if args.scrape:
        step_scrape(years=args.years, skip_details=args.skip_details)

    if args.join:
        step_join()

    if args.pack:
        step_pack()

    if not any([args.projects, args.reorganize, args.scrape, args.join, args.pack]):
        parser.print_help()

if __name__ == "__main__":
    main()
