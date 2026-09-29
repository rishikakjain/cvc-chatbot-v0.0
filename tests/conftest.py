"""
Shared fixtures for the CVC chatbot test suite.
"""

import pytest
import openpyxl
from pathlib import Path
from datetime import datetime

import tools.filter_courses as fc_module

DOCUMENTS_DIR = Path(__file__).parent.parent / "documents"
DATA_PATH = Path(__file__).parent.parent / "data" / "courses.json"


@pytest.fixture(autouse=True)
def clear_courses_cache():
    fc_module._courses_cache = None
    yield
    fc_module._courses_cache = None


def _load_excel_rows() -> list[dict]:
    """Load all rows from both Excel exports into a flat list of dicts."""
    rows = []
    for xlsx in sorted(DOCUMENTS_DIR.glob("*.xlsx")):
        wb = openpyxl.load_workbook(xlsx, read_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        headers = all_rows[0]
        for row in all_rows[1:]:
            rows.append(dict(zip(headers, row)))
    return rows


def _parse_ge_codes(raw) -> list[str]:
    """Split pipe- or comma-separated GE codes into a list."""
    if not raw:
        return []
    return [c.strip() for c in str(raw).replace("|", ",").split(",") if c.strip()]


@pytest.fixture(scope="session")
def excel_rows():
    """All course rows from both Excel exports, loaded once per session."""
    return _load_excel_rows()


@pytest.fixture(scope="session")
def excel_by_crn(excel_rows):
    """Dict keyed by CRN (UUID string) for fast exact lookups."""
    return {str(row["CRN"]): row for row in excel_rows if row.get("CRN")}


@pytest.fixture(scope="session")
def excel_csu_codes(excel_rows):
    """Set of all CSU Breadth codes present in the Excel data."""
    codes = set()
    for row in excel_rows:
        codes.update(_parse_ge_codes(row.get("CSU Breadth Requirements")))
    return codes


@pytest.fixture(scope="session")
def excel_igetc_codes(excel_rows):
    """Set of all IGETC codes present in the Excel data."""
    codes = set()
    for row in excel_rows:
        codes.update(_parse_ge_codes(row.get("IGETC Requirements")))
    return codes


@pytest.fixture(scope="session")
def excel_calgetc_codes(excel_rows):
    """Set of all Cal-GETC codes present in the Excel data."""
    codes = set()
    for row in excel_rows:
        codes.update(_parse_ge_codes(row.get("Cal-GETC Requirements")))
    return codes
