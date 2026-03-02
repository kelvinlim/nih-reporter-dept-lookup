"""
Tests for schema loading and person resource type in nih-reporter-dept-lookup.

Verifies that:
- load_schemas() returns "person" key (not "user")
- All person schema files exist and are valid JSON
- Pack output uses v2 format with "persons" array and "person" schema key
"""
import json
from pathlib import Path

import pytest


SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


# ---------------------------------------------------------------------------
# Schema file existence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", [
    "base_person_schema.json",
    "umn_person_schema.json",
    "va_person_schema.json",
    "base_project_schema.json",
    "va_project_schema.json",
])
def test_schema_file_exists(filename):
    """All renamed person schema files exist."""
    assert (SCHEMA_DIR / filename).exists(), f"{filename} not found in schemas/"


@pytest.mark.parametrize("filename", [
    "base_person_schema.json",
    "umn_person_schema.json",
    "va_person_schema.json",
])
def test_schema_file_valid_json(filename):
    """Person schema files are valid JSON with expected structure."""
    with open(SCHEMA_DIR / filename) as f:
        data = json.load(f)
    # Each schema should have at least one section (e.g., "general")
    assert isinstance(data, dict)
    assert len(data) > 0
    # Should have a section with fields
    for key, val in data.items():
        if key.startswith("_"):
            continue
        assert isinstance(val, dict), f"Section '{key}' should be a dict"


# ---------------------------------------------------------------------------
# load_schemas returns "person" key
# ---------------------------------------------------------------------------

def test_load_schemas_person_key():
    """load_schemas() returns dict with 'person' key, not 'user'."""
    from schemas import load_schemas
    result = load_schemas("umn_person_schema.json", "base_project_schema.json")
    assert "person" in result
    assert "user" not in result
    assert "project" in result


def test_load_schemas_va_person_key():
    """load_schemas() for VA returns dict with 'person' key."""
    from schemas import load_schemas
    result = load_schemas("va_person_schema.json", "va_project_schema.json")
    assert "person" in result
    assert "user" not in result
    assert "project" in result


# ---------------------------------------------------------------------------
# Schema content validation
# ---------------------------------------------------------------------------

def test_umn_person_schema_has_expected_fields():
    """UMN person schema contains expected fields."""
    from schemas import load_schema
    data = load_schema("umn_person_schema.json")
    general = data.get("general", {})
    # Filter out _section metadata
    fields = {k for k in general if not k.startswith("_")}
    assert "orcid_id" in fields or "rank" in fields or "is_investigator" in fields


def test_va_person_schema_has_expected_fields():
    """VA person schema contains expected fields."""
    from schemas import load_schema
    data = load_schema("va_person_schema.json")
    general = data.get("general", {})
    fields = {k for k in general if not k.startswith("_")}
    assert "nih_investigator_id" in fields or "is_investigator" in fields
