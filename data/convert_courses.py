"""
Converts XLSX course exports from CVC into a single normalized courses.json.

Input:  documents/*.xlsx (Victor Valley College + Cuesta College)
Output: data/courses.json
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

XLSX_FILES = [
    Path(__file__).parent.parent / "documents" / "8c315095-5d05-4e67-84bb-1b0eac3eded6-csv_export.xlsx",
    Path(__file__).parent.parent / "documents" / "d15ac409-2257-4ec1-97a3-71ea7328744d-csv_export.xlsx",
]

OUTPUT_PATH = Path(__file__).parent / "courses.json"

COLUMN_MAP = {
    "Course Code":              "courseCode",
    "Course Name":              "courseName",
    "CID":                      "cid",
    "Section":                  "section",
    "CRN":                      "crn",
    "Start Date":               "startDate",
    "End Date":                 "endDate",
    "Term":                     "term",
    "Teaching College":         "teachingCollege",
    "Delivery Method":          "deliveryMethod",
    "Badges":                   "badges",
    "CSU Breadth Requirements": "csuBreadth",
    "IGETC Requirements":       "igetc",
    "Cal-GETC Requirements":    "calGetc",
    "Professors":               "professors",
    "Units":                    "units",
    "Visible":                  "visible",
    "Filter Applied":           "filterApplied",
    "Course Notes":             "courseNotes",
    "Seat Count":               "seatCount",
    "Seats Available":          "seatsAvailable",
    "Seat Count Last Updated at": "seatCountUpdatedAt",
}

# Excel epoch starts 1900-01-01 (with Lotus 1-2-3 leap-year bug: day 60 = Feb 29 1900, nonexistent)
EXCEL_EPOCH = datetime(1899, 12, 30, tzinfo=timezone.utc)


def excel_date_to_iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            dt = EXCEL_EPOCH.replace(tzinfo=None) + __import__("datetime").timedelta(days=float(value))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value) if value else None


def split_pipe(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in str(value).split("|") if v.strip()]


def split_badges(value: str | None) -> list[str]:
    if not value:
        return []
    # Badges are space-separated but badge names contain spaces; known badges:
    known = [
        "Low Textbook Cost (LTC)",
        "Open Educational Resources (OER)",
        "Quality Reviewed",
        "Web-Enhanced",
    ]
    found = []
    remaining = str(value)
    for badge in known:
        if badge in remaining:
            found.append(badge)
            remaining = remaining.replace(badge, "")
    # Catch any unknown badges left over
    extra = [b.strip() for b in re.split(r"\s{2,}", remaining) if b.strip()]
    return found + extra


def parse_row(headers: list[str], row) -> dict | None:
    raw = {headers[i]: (cell.value if hasattr(cell, "value") else cell) for i, cell in enumerate(row) if i < len(headers)}

    # Skip courses marked not visible
    if str(raw.get("Visible", "Yes")).strip().lower() == "no":
        return None

    course = {}
    for xlsx_col, json_key in COLUMN_MAP.items():
        val = raw.get(xlsx_col)

        if json_key in ("csuBreadth", "igetc", "calGetc"):
            course[json_key] = split_pipe(val)
        elif json_key == "badges":
            course[json_key] = split_badges(val)
        elif json_key in ("startDate", "endDate"):
            course[json_key] = excel_date_to_iso(val)
        elif json_key == "seatCountUpdatedAt":
            course[json_key] = excel_date_to_iso(val)
        elif json_key in ("seatCount", "seatsAvailable", "units"):
            try:
                course[json_key] = int(val) if val is not None else None
            except (ValueError, TypeError):
                course[json_key] = None
        elif json_key == "courseCode":
            code = str(val).strip() if val is not None else None
            # Normalise "MATH232" → "MATH 232", "BIO101A" → "BIO 101A"
            if code:
                code = re.sub(r'^([A-Za-z]+)(\d)', r'\1 \2', code)
            course[json_key] = code
        elif json_key == "crn":
            # CRN is a UUID string in this dataset
            course[json_key] = str(val).strip() if val is not None else None
        elif json_key in ("visible", "filterApplied"):
            course[json_key] = str(val).strip().lower() == "yes" if val is not None else False
        else:
            course[json_key] = str(val).strip() if val is not None else None

    # Require minimum fields to be a valid record
    if not course.get("courseCode") or not course.get("teachingCollege"):
        return None

    return course


def convert(xlsx_paths: list[Path]) -> list[dict]:
    all_courses = []
    for path in xlsx_paths:
        if not path.exists():
            print(f"  WARNING: file not found: {path}")
            continue
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = iter(ws.rows)
        header_row = next(rows)
        headers = [cell.value for cell in header_row]
        count = 0
        for row in rows:
            course = parse_row(headers, row)
            if course:
                all_courses.append(course)
                count += 1
        print(f"  {path.name}: {count} courses loaded")
        wb.close()
    return all_courses


if __name__ == "__main__":
    print("Converting XLSX files to courses.json...")
    courses = convert(XLSX_FILES)
    OUTPUT_PATH.write_text(json.dumps(courses, indent=2))
    print(f"\nTotal: {len(courses)} courses written to {OUTPUT_PATH}")

    # Quick validation report
    colleges = {}
    ge_missing = 0
    for c in courses:
        col = c["teachingCollege"]
        colleges[col] = colleges.get(col, 0) + 1
        if not c["csuBreadth"] and not c["igetc"] and not c["calGetc"]:
            ge_missing += 1

    print("\nBy college:")
    for col, n in sorted(colleges.items()):
        print(f"  {col}: {n}")
    print(f"\nCourses with no GE area tags: {ge_missing} ({ge_missing/len(courses)*100:.0f}%)")
    print("  (vocational/workforce courses — expected)")
