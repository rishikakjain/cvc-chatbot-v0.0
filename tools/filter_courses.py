"""
filter_courses — core course search tool for the CVC chatbot.

Accepts structured filter parameters and returns the top N matching courses
sorted by seats available descending.

This module is pure Python with no AWS dependencies — fully testable locally.
In Lambda, the handler wraps this function and reads courses from S3.
"""

import json
import math
import sys
from datetime import date as _date
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.college_locations import get_college_coords

_IN_PERSON_POSITIVE = (
    "proctored",
    "testing center",
    "must attend in-person",
    "must attend in person",
    "required to attend in-person",
    "required to attend in person",
    "required attendance",
    "on-campus orientation",
    "on campus orientation",
    "in-person midterm",
    "in-person final",
    "in-person lab",
    "on-site",
)

# If the note contains "in-person" or "in person" but also one of these negation
# phrases nearby, it does NOT count as a real in-person requirement.
_IN_PERSON_NEGATIONS = (
    "no mandatory in-person",
    "no in-person",
    "not in-person",
    "without in-person",
    "no mandatory in person",
    "no in person",
)


def _has_in_person_requirement(course: dict) -> bool:
    notes = (course.get("courseNotes") or "").lower()
    # Negations take priority over all positive signals
    if any(neg in notes for neg in _IN_PERSON_NEGATIONS):
        return False
    if any(kw in notes for kw in _IN_PERSON_POSITIVE):
        return True
    # Generic "in-person" / "in person" phrase when not negated
    return "in-person" in notes or "in person" in notes


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _course_duration_weeks(course: dict) -> float | None:
    start = course.get("startDate")
    end = course.get("endDate")
    if not start or not end:
        return None
    try:
        return (_date.fromisoformat(end) - _date.fromisoformat(start)).days / 7
    except ValueError:
        return None


def _is_ztc(course: dict) -> bool:
    badges = course.get("badges") or []
    notes_lower = (course.get("courseNotes") or "").lower()
    return (
        any("zero textbook" in str(b).lower() for b in badges)
        or "zero textbook" in notes_lower
        or " ztc" in notes_lower
        or "(ztc)" in notes_lower
        or notes_lower.startswith("ztc")
    )


def _rank_score(course: dict) -> float:
    seats = max(0, course.get("seatsAvailable") or 0)
    total = max(1, course.get("seatCount") or seats or 1)

    # Seat availability (0–40 pts): blend log-scaled absolute count + fill rate
    # so both "many seats" and "high availability ratio" are rewarded
    abs_score = min(math.log2(seats + 1) / math.log2(33), 1.0) * 20
    fill_score = (seats / total) * 20
    seat_score = abs_score + fill_score

    # ZTC bonus (15 pts)
    ztc_score = 15 if _is_ztc(course) else 0

    # GE breadth (0–10 pts): more GE areas = more broadly useful
    ge_count = len(
        (course.get("csuBreadth") or [])
        + (course.get("igetc") or [])
        + (course.get("calGetc") or [])
    )
    ge_score = min(ge_count, 5) * 2

    # Start date proximity (0–15 pts): prefer courses starting soon
    start = course.get("startDate")
    date_score = 0
    if start:
        try:
            days_away = (_date.fromisoformat(start) - _date.today()).days
            if days_away < 0:
                date_score = 0
            elif days_away <= 14:
                date_score = 15
            elif days_away <= 45:
                date_score = 12
            elif days_away <= 90:
                date_score = 8
            elif days_away <= 180:
                date_score = 4
        except ValueError:
            pass

    return seat_score + ztc_score + ge_score + date_score

_courses_cache: list[dict] | None = None


def load_courses(source_path: str | Path | None = None) -> list[dict]:
    """
    Load course data. v0.1: reads from SQLite (courses.db).
    Falls back to JSON when source_path points to a .json file (keeps tests working).
    v1.0 hook: replace body with live API call, keep signature.
    """
    global _courses_cache
    if _courses_cache is not None:
        return _courses_cache

    if source_path is not None:
        sp = Path(source_path)
        if sp.suffix == ".json":
            with open(sp) as f:
                _courses_cache = json.load(f)
            return _courses_cache
        # Explicit SQLite path passed in (e.g. from tests)
        from data.db import get_db, row_to_dict
        conn = get_db(sp)
        rows = conn.execute("SELECT * FROM courses WHERE visible = 1").fetchall()
        _courses_cache = [row_to_dict(r) for r in rows]
        return _courses_cache

    from data.db import get_connection, execute
    conn = get_connection()
    _courses_cache = execute(conn, "SELECT * FROM courses WHERE visible = TRUE")
    return _courses_cache


def filter_courses(
    ge_areas: list[str] | None = None,
    subject_keyword: str | None = None,
    delivery_method: str | None = None,
    exclude_college: str | None = None,
    start_after: str | None = None,
    has_seats: bool = True,
    ztc: bool = False,
    top_n: int = 10,
    source_path: str | Path | None = None,
    max_distance_miles: float | None = None,
    home_college_name: str | None = None,
    condensed_only: bool = False,
    max_duration_weeks: int | None = None,
    region: str | None = None,
) -> list[dict]:
    """
    Filter courses and return top_n results.

    Args:
        ge_areas:           List of GE area codes to match (any of; e.g. ["B1","B3"]).
        subject_keyword:    Free-text keyword matched against courseName.
        delivery_method:    "async" | "sync" | None.
        exclude_college:    Student's home college to exclude from results.
        start_after:        ISO date string "YYYY-MM-DD".
        has_seats:          Only return courses with seatsAvailable > 0.
        top_n:              Max results to return.
        source_path:        Override path to courses.json (for testing).
        max_distance_miles: Drop courses with in-person requirements from colleges
                            farther than this many miles from home_college_name.
        home_college_name:  Student's home college — used as the distance origin.
        condensed_only:     If True, only return courses ≤ 10 weeks long (alias for max_duration_weeks=10).
        max_duration_weeks: Maximum course length in weeks. Courses with no date data pass.
        region:             CA geographic region to filter teaching colleges (e.g. "Bay Area").

    Returns:
        List of course dicts, ranked by composite score, capped at top_n.
    """
    courses = load_courses(source_path)
    results = []

    # Expand bare parent codes to sub-codes present in data
    # e.g. "5" → ["5A","5B","5C"], "4" → ["4","4A",...,"4J"], "D" → ["D","D1",...,"D9"]
    if ge_areas:
        expanded = []
        all_codes = set()
        for c in courses:
            for field in ("csuBreadth", "igetc", "calGetc"):
                all_codes.update(c.get(field) or [])
        for code in ge_areas:
            cu = code.upper()
            children = [c for c in all_codes if c.upper().startswith(cu) and c.upper() != cu]
            if children:
                expanded.extend(children)
            else:
                expanded.append(code)
        ge_areas = expanded

    delivery_filter = None
    if delivery_method:
        dl = delivery_method.lower()
        if "async" in dl:
            delivery_filter = "online - asynchronous"
        elif "sync" in dl:
            delivery_filter = "online - synchronous"

    keyword = subject_keyword.lower().strip() if subject_keyword else None

    for course in courses:
        # Exclude student's home college
        if exclude_college and exclude_college.lower() in course.get("teachingCollege", "").lower():
            continue

        # Delivery method filter
        if delivery_filter:
            course_delivery = (course.get("deliveryMethod") or "").lower()
            if delivery_filter not in course_delivery:
                continue

        # Seats filter
        if has_seats:
            seats = course.get("seatsAvailable")
            if seats is None or seats <= 0:
                continue

        # Start date filter
        if start_after and course.get("startDate"):
            if course["startDate"] < start_after:
                continue

        # GE area filter — course must match at least one of the requested codes
        if ge_areas:
            course_areas = (
                (course.get("csuBreadth") or [])
                + (course.get("igetc") or [])
                + (course.get("calGetc") or [])
            )
            course_areas_upper = [a.upper() for a in course_areas]
            if not any(code.upper() in course_areas_upper for code in ge_areas):
                continue

        # ZTC filter — badge field or courseNotes mentioning ZTC
        if ztc:
            if not _is_ztc(course):
                continue

        # Duration filter — condensed_only is a backward-compatible alias
        effective_max_weeks = max_duration_weeks
        if condensed_only and effective_max_weeks is None:
            effective_max_weeks = 10
        if effective_max_weeks is not None:
            weeks = _course_duration_weeks(course)
            if weeks is not None and weeks > effective_max_weeks:
                continue

        # Region filter — drop courses from colleges outside the requested CA region
        if region:
            from data.college_regions import get_college_region
            college_lower = (course.get("teachingCollege") or "").lower()
            if get_college_region(college_lower) != region:
                continue

        # Subject keyword filter — matches against course name
        if keyword:
            name = (course.get("courseName") or "").lower()
            if keyword not in name:
                continue

        results.append(course)

    # Distance filter — only affects courses with in-person requirements
    if max_distance_miles is not None and home_college_name:
        origin = get_college_coords(home_college_name)
        if origin:
            filtered = []
            for course in results:
                if not _has_in_person_requirement(course):
                    filtered.append(course)
                    continue
                dest = get_college_coords(course.get("teachingCollege", ""))
                if dest is None:
                    filtered.append(course)  # unknown location — include it
                    continue
                dist = _haversine_miles(origin[0], origin[1], dest[0], dest[1])
                if dist <= max_distance_miles:
                    filtered.append(course)
            results = filtered

    results.sort(key=lambda c: -_rank_score(c))

    return results[:top_n]


def _normalize_name(name: str | None) -> str | None:
    """Title-case a course name if it is all-uppercase, leave mixed-case alone."""
    if not name:
        return name
    stripped = name.strip()
    if stripped == stripped.upper():
        return stripped.title()
    return stripped


def summarize_course(course: dict) -> dict:
    """
    Return a chatbot-friendly summary of a course record.
    Only includes fields the LLM needs to describe the course — not internal UUIDs.
    """
    ge_tags = []
    for field, label in [("csuBreadth", "CSU"), ("igetc", "IGETC"), ("calGetc", "Cal-GETC")]:
        codes = course.get(field) or []
        if codes:
            ge_tags.append(f"{label}: {', '.join(codes)}")

    available = course.get("seatsAvailable")
    total = course.get("seatCount")
    # Clamp negative seat counts to 0 (data quality issue in source CSV)
    if available is not None:
        available = max(0, int(available))
    if available is not None and total:
        seats_str = f"{available} out of {total}"
    elif available is not None:
        seats_str = str(available)
    else:
        seats_str = None

    # Build flat GE tag list with framework prefix so the frontend can colour-code them
    # Format: ["CSU B4", "IGETC 2A", "Cal-GETC 2"]
    ge_chips = []
    for code in (course.get("csuBreadth") or []):
        ge_chips.append(f"CSU {code}")
    for code in (course.get("igetc") or []):
        ge_chips.append(f"IGETC {code}")
    for code in (course.get("calGetc") or []):
        ge_chips.append(f"Cal-GETC {code}")

    units = course.get("units")
    if units is not None:
        units = units if units > 0 else None  # treat 0-unit courses as unknown

    badges = course.get("badges") or []
    notes_lower = str(course.get("courseNotes") or "").lower()
    is_ztc = _is_ztc(course)

    return {
        "courseCode": course.get("courseCode"),
        "courseName": _normalize_name(course.get("courseName")),
        "teachingCollege": course.get("teachingCollege"),
        "units": units,
        "deliveryMethod": course.get("deliveryMethod"),
        "startDate": course.get("startDate"),
        "endDate": course.get("endDate"),
        "availableSeats": seats_str,
        "professors": course.get("professors"),
        "badges": badges,
        "isZtc": is_ztc,
        "geChips": ge_chips,
        "courseNotes": _normalize_name(course.get("courseNotes")),
    }
