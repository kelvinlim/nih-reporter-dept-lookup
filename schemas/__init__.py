"""Shared schema loading and CPOS pre-computation utilities for Runway export."""

import json
import math
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent


def load_schema(filename):
    """Load a schema JSON file from the schemas directory."""
    with open(SCHEMA_DIR / filename, "r") as f:
        return json.load(f)


def load_schemas(user_schema_file, project_schema_file):
    """Load user and project schemas, returning the combined dict for Runway import."""
    return {
        "user": load_schema(user_schema_file),
        "project": load_schema(project_schema_file),
    }


def _estimate_project_years(start_str, end_str):
    """Estimate project duration in years from date strings (YYYY-MM-DD)."""
    if not start_str or not end_str:
        return None
    try:
        from datetime import date
        s = date.fromisoformat(start_str[:10])
        e = date.fromisoformat(end_str[:10])
        days = (e - s).days
        if days <= 0:
            return None
        return max(1, math.ceil(days / 365.25))
    except (ValueError, TypeError):
        return None


def precompute_cpos(attributes, status, abstract=None, location=None, use_total_award=False):
    """
    Derive CPOS fields from grant_info attributes.

    Args:
        attributes: dict of project attributes (grant_info.* keys)
        status: project status string ("current", "pending", "completed")
        abstract: optional abstract text for cpos.overall_objectives
        location: optional location string for cpos.location
        use_total_award: if True, prefer grant_info.total_award_amount over
                         the FY amount × years calculation

    Returns:
        dict of cpos.* key-value pairs (only non-None values)
    """
    cpos = {}

    # Award number
    award_num = attributes.get("grant_info.award_number")
    if award_num:
        cpos["cpos.award_number"] = award_num

    # Award amount: use total_award if available and preferred, else FY × years
    if use_total_award:
        total = attributes.get("grant_info.total_award_amount")
        if total is not None:
            cpos["cpos.award_amount"] = str(int(total))
        else:
            # Fall back to FY calculation
            fy_amt = attributes.get("grant_info.award_amount")
            if fy_amt is not None:
                years = _estimate_project_years(
                    attributes.get("grant_info.project_start_date"),
                    attributes.get("grant_info.project_end_date"),
                )
                total_calc = int(fy_amt * years) if years else int(fy_amt)
                cpos["cpos.award_amount"] = str(total_calc)
    else:
        fy_amt = attributes.get("grant_info.award_amount")
        if fy_amt is not None:
            years = _estimate_project_years(
                attributes.get("grant_info.project_start_date"),
                attributes.get("grant_info.project_end_date"),
            )
            total_calc = int(fy_amt * years) if years else int(fy_amt)
            cpos["cpos.award_amount"] = str(total_calc)

    # Support type from status
    if status in ("current", "pending"):
        cpos["cpos.support_type"] = status

    # Support source from funding agency (CPOS limit: 60 chars)
    agency = attributes.get("grant_info.funding_agency")
    if agency:
        cpos["cpos.support_source"] = agency[:60]

    # Dates
    start = attributes.get("grant_info.project_start_date")
    if start:
        cpos["cpos.project_start_date"] = start
    end = attributes.get("grant_info.project_end_date")
    if end:
        cpos["cpos.project_end_date"] = end

    # Static defaults
    cpos["cpos.contribution_type"] = "award"
    cpos["cpos.potential_overlap"] = "None"

    # Location
    if location:
        cpos["cpos.location"] = location

    # Abstract → overall objectives (CPOS limit: 1500 chars)
    if abstract:
        cpos["cpos.overall_objectives"] = abstract[:1500]

    return cpos
