"""
filter_courses — core course search tool for the CVC chatbot.

Accepts structured filter parameters and returns the top N matching courses
sorted by seats available descending.

This module is pure Python with no AWS dependencies — fully testable locally.
In Lambda, the handler wraps this function and reads courses from S3.
"""

import json
from pathlib import Path
from typing import Optional

_courses_cache: list[dict] | None = None


def load_courses(source_path: str | Path | None = None) -> list[dict]:
    """
    Load course data. v0.0: reads from local/S3 JSON file.
    v0.1 hook: replace body with live API call, keep signature.
    """
    global _courses_cache
    if _courses_cache is not None:
        return _courses_cache

    if source_path is None:
        source_path = Path(__file__).parent.parent / "data" / "courses.json"

    with open(source_path) as f:
        _courses_cache = json.load(f)

    return _courses_cache


def filter_courses(
    ge_areas: list[str] | None = None,
    delivery_method: str | None = None,
    exclude_college: str | None = None,
    start_after: str | None = None,
    has_seats: bool = True,
    top_n: int = 5,
    source_path: str | Path | None = None,
) -> list[dict]:
    """
    Filter courses and return top_n results.

    Args:
        ge_areas:        List of GE area codes to match (any of; e.g. ["B1","B3"]).
                         Checks csuBreadth, igetc, and calGetc fields.
                         None = no GE filter (returns all subjects).
        delivery_method: "async" | "sync" | None (no filter).
        exclude_college: Exact teaching college name to exclude (student's home college).
                         v0.1 hook: this param will also trigger ASSIST crosswalk lookup.
        start_after:     ISO date string "YYYY-MM-DD"; exclude courses starting before this.
        has_seats:       If True, only return courses with seatsAvailable > 0.
        top_n:           Max results to return.
        source_path:     Override path to courses.json (for testing).

    Returns:
        List of course dicts, sorted by seatsAvailable descending, capped at top_n.
    """
    courses = load_courses(source_path)
    results = []

    delivery_filter = None
    if delivery_method:
        dl = delivery_method.lower()
        if "async" in dl:
            delivery_filter = "online - asynchronous"
        elif "sync" in dl:
            delivery_filter = "online - synchronous"

    for course in courses:
        # Exclude student's home college
        if exclude_college and course.get("teachingCollege", "").lower() == exclude_college.lower():
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

        results.append(course)

    # Sort by seats available descending, then by start date ascending
    results.sort(
        key=lambda c: (-(c.get("seatsAvailable") or 0), c.get("startDate") or "")
    )

    return results[:top_n]


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

    return {
        "courseCode": course.get("courseCode"),
        "courseName": course.get("courseName"),
        "teachingCollege": course.get("teachingCollege"),
        "units": course.get("units"),
        "deliveryMethod": course.get("deliveryMethod"),
        "startDate": course.get("startDate"),
        "endDate": course.get("endDate"),
        "seatsAvailable": course.get("seatsAvailable"),
        "seatCount": course.get("seatCount"),
        "professors": course.get("professors"),
        "badges": course.get("badges") or [],
        "geTags": ge_tags,
        "courseNotes": course.get("courseNotes"),
    }
