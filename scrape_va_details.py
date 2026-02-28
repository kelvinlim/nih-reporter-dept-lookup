import requests
import time
import re
from bs4 import BeautifulSoup

VA_BASE_URL = "https://www.research.va.gov/about/funded_research"
VA_LISTING_URL = VA_BASE_URL + "/projects-FY{year}.cfm"
VA_DETAIL_URL = VA_BASE_URL + "/proj-details-FY{year}.cfm?pid={pid}"


def scrape_listing_page(year):
    """
    Scrape a single fiscal year's project listing page.
    Returns a list of dicts: { project_num, pid, title, pi_name, listing_column_name,
                               listing_column_value, fiscal_year }
    """
    url = VA_LISTING_URL.format(year=year)
    print(f"  Fetching listing page: FY{year}...")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching listing for FY{year}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the project table by looking for a table with "Project No." header
    table = None
    headers = []
    for t in soup.find_all("table"):
        ths = t.find_all("th")
        if ths:
            h = [th.get_text(strip=True) for th in ths]
            if any("Project" in col for col in h):
                table = t
                headers = h
                break

    if not table:
        print(f"  Warning: Could not find project table for FY{year}")
        return []

    # Determine what the 4th column is (varies by year: "Location" or "Service")
    fourth_col_name = headers[3] if len(headers) > 3 else "Unknown"

    entries = []
    rows = table.find_all("tr")[1:]  # skip header row

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        # First cell has link: <a href="proj-details-FY2025.cfm?pid=762756">IK2RX004298-01A1</a>
        link = cells[0].find("a")
        if not link:
            continue

        project_num = link.get_text(strip=True)
        href = link.get("href", "")

        # Extract pid from href
        pid_match = re.search(r'pid=(\d+)', href)
        pid = pid_match.group(1) if pid_match else None

        title = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        pi_name = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        fourth_col_value = cells[3].get_text(strip=True) if len(cells) > 3 else ""

        entries.append({
            "project_num": project_num,
            "pid": pid,
            "title": title,
            "pi_name": pi_name,
            "listing_column_name": fourth_col_name,
            "listing_column_value": fourth_col_value,
            "fiscal_year": year
        })

    print(f"  Found {len(entries)} projects in FY{year} listing")
    return entries


def scrape_detail_page(year, pid):
    """
    Scrape a single project detail page.
    Returns dict with: total_award_amount, project_period, location,
                       congressional_district, research_service
    """
    url = VA_DETAIL_URL.format(year=year, pid=pid)

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"    Error fetching detail for pid={pid}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text()

    details = {}

    # Total Award Amount: $1,829,446
    amount_match = re.search(r'Total Award Amount:\s*\$?([\d,]+)', text)
    if amount_match:
        details["total_award_amount"] = int(amount_match.group(1).replace(",", ""))

    # Project Period: April 2023 - March 2028
    period_match = re.search(r'Project Period:\s*(.+?)(?:\n|$)', text)
    if period_match:
        details["project_period"] = period_match.group(1).strip()

    # Location: Hines, IL
    location_match = re.search(r'Location:\s*(.+?)(?:\n|$)', text)
    if location_match:
        details["location"] = location_match.group(1).strip()

    # Congressional District Code: 7
    district_match = re.search(r'Congressional District Code:\s*(\d+)', text)
    if district_match:
        details["congressional_district"] = district_match.group(1)

    # Portfolio (FY2026+) or Research Service (older years)
    portfolio_match = re.search(r'Portfolio:\s*(.+?)(?:\n|$)', text)
    if portfolio_match:
        details["portfolio"] = portfolio_match.group(1).strip()

    service_match = re.search(r'Research Service:\s*(.+?)(?:\n|$)', text)
    if service_match:
        details["research_service"] = service_match.group(1).strip()

    return details


def build_listing_index(years):
    """
    Scrape all listing pages for given years and build a mapping:
      { project_num: { pid, fiscal_year, ... } }

    Keeps the most recent year's entry if a project appears in multiple years.
    """
    index = {}
    for year in years:
        entries = scrape_listing_page(year)
        for entry in entries:
            proj_num = entry["project_num"]
            # Keep the most recent year's entry if duplicate
            if proj_num not in index or entry["fiscal_year"] > index[proj_num]["fiscal_year"]:
                index[proj_num] = entry
        time.sleep(1)
    return index


if __name__ == "__main__":
    # Test: scrape FY2025 listing page
    entries = scrape_listing_page(2025)
    print(f"\nTotal entries: {len(entries)}")
    if entries:
        print(f"Sample entry: {entries[0]}")

        # Test: scrape one detail page
        sample = entries[0]
        if sample["pid"]:
            print(f"\nScraping detail for {sample['project_num']} (pid={sample['pid']})...")
            detail = scrape_detail_page(2025, sample["pid"])
            print(f"Detail: {detail}")
