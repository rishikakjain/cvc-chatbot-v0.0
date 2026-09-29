"""
Build courses.db from XLSX source files.

Usage:
    python data/build_db.py

Produces data/courses.db, replacing any existing file.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.college_locations import COLLEGE_LOCATIONS
from data.college_regions import get_college_region
from data.convert_courses import XLSX_FILES, convert
from data.db import get_db, init_db

DB_PATH = Path(__file__).parent / "courses.db"


def build(db_path: Path = DB_PATH) -> int:
    if db_path.exists():
        db_path.unlink()

    conn = get_db(db_path)
    init_db(conn)

    # Populate colleges table from static coordinates + region assignments
    for name_lower, (lat, lng) in COLLEGE_LOCATIONS.items():
        region = get_college_region(name_lower)
        name_display = name_lower.title()
        conn.execute(
            "INSERT OR IGNORE INTO colleges (name, name_lower, lat, lng, region) VALUES (?, ?, ?, ?, ?)",
            (name_display, name_lower, lat, lng, region),
        )
    conn.commit()

    print("Loading courses from XLSX files...")
    courses = convert(XLSX_FILES)
    print(f"Loaded {len(courses)} courses from source files.")

    inserted = 0
    skipped = 0
    for c in courses:
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO courses (
                    course_code, course_name, cid, section, crn,
                    start_date, end_date, term, teaching_college, delivery_method,
                    badges, csu_breadth, igetc, cal_getc,
                    professors, units, visible, filter_applied,
                    course_notes, seat_count, seats_available, seat_count_updated_at,
                    source_file
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?
                )
                """,
                (
                    c.get("courseCode"),
                    c.get("courseName"),
                    c.get("cid"),
                    c.get("section"),
                    c.get("crn"),
                    c.get("startDate"),
                    c.get("endDate"),
                    c.get("term"),
                    c.get("teachingCollege"),
                    c.get("deliveryMethod"),
                    json.dumps(c.get("badges") or []),
                    json.dumps(c.get("csuBreadth") or []),
                    json.dumps(c.get("igetc") or []),
                    json.dumps(c.get("calGetc") or []),
                    c.get("professors"),
                    c.get("units"),
                    1 if c.get("visible") else 0,
                    1 if c.get("filterApplied") else 0,
                    c.get("courseNotes"),
                    c.get("seatCount"),
                    c.get("seatsAvailable"),
                    c.get("seatCountUpdatedAt"),
                    None,
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"  WARNING: skipped {c.get('crn')}: {e}")
            skipped += 1

    conn.commit()
    conn.close()
    print(f"Inserted {inserted} courses ({skipped} skipped) into {db_path}")
    return inserted


if __name__ == "__main__":
    build()
