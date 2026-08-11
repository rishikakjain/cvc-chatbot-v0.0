"""
Card integrity tests — validate that every field in a course card
is correctly populated from raw data all the way to the frontend shape.

Three layers tested:
  1. summarize_course()  — raw course dict → API response shape
  2. Live API            — real API responses have correct field types/values
  3. apiCourseToCourseCard mapping — simulated in Python to catch frontend bugs

Run:
    python3 -m pytest tests/test_card_integrity.py -v
"""

import re
import uuid
import pytest
import requests
from pathlib import Path

# ── Shared helpers ────────────────────────────────────────────────────────────

API_URL = "https://9koj0054n8.execute-api.us-west-2.amazonaws.com/chat"
DATA_PATH = Path(__file__).parent.parent / "data" / "courses.json"


def api_chat(message):
    resp = requests.post(
        API_URL,
        json={"message": message},
        headers={"Content-Type": "application/json", "X-Session-Id": str(uuid.uuid4())},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fmt_date(iso):
    """Mirror of frontend fmtDate()."""
    if not iso:
        return ""
    parts = iso.split("-")
    if len(parts) != 3:
        return ""
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return f"{months[m-1]} {d}, {y}"


def api_course_to_card(course, index):
    """Mirror of frontend apiCourseToCourseCard()."""
    seats_available = None
    seats_total = None
    avail = course.get("availableSeats", "")
    if avail:
        match = re.search(r"(\d+)\s+out\s+of\s+(\d+)", str(avail), re.I)
        if match:
            seats_available = int(match.group(1))
            seats_total = int(match.group(2))
    units = course.get("units")
    if isinstance(units, str):
        try:
            units = float(units) or None
        except ValueError:
            units = None
    return {
        "index": index,
        "name": course.get("courseName") or "",
        "code": course.get("courseCode") or "",
        "units": units,
        "college": course.get("teachingCollege") or "",
        "delivery": course.get("deliveryMethod") or "",
        "startDate": fmt_date(course.get("startDate")),
        "endDate": fmt_date(course.get("endDate")),
        "professor": course.get("professors") or "",
        "note": course.get("courseNotes") or "",
        "ge": course.get("geChips") if isinstance(course.get("geChips"), list) else [],
        "seatsAvailable": seats_available,
        "seatsTotal": seats_total,
    }


# ── Layer 1: summarize_course() unit tests ────────────────────────────────────

import json as _json
import tools.filter_courses as fc_module
from tools.filter_courses import load_courses, summarize_course

@pytest.fixture(autouse=True)
def clear_cache():
    fc_module._courses_cache = None
    yield
    fc_module._courses_cache = None


class TestSummarizeCourse:
    """Validate summarize_course() output shape against the frontend's expectations."""

    REQUIRED_KEYS = {
        "courseCode", "courseName", "teachingCollege", "units",
        "deliveryMethod", "startDate", "endDate", "availableSeats",
        "professors", "badges", "geChips", "courseNotes",
    }

    def test_all_required_keys_present(self):
        courses = load_courses(DATA_PATH)
        for course in courses:
            s = summarize_course(course)
            missing = self.REQUIRED_KEYS - set(s.keys())
            assert not missing, f"Missing keys in {course.get('courseCode')}: {missing}"

    def test_ge_chips_format(self):
        """geChips must be a list of 'FRAMEWORK CODE' strings."""
        courses = load_courses(DATA_PATH)
        for course in courses:
            s = summarize_course(course)
            assert isinstance(s["geChips"], list), f"geChips not a list for {course.get('courseCode')}"
            for chip in s["geChips"]:
                assert isinstance(chip, str), f"Non-string chip: {chip}"
                assert re.match(r'^(CSU|IGETC|Cal-GETC)\s+\S+', chip), \
                    f"Chip doesn't match 'FRAMEWORK CODE': {chip!r} in {course.get('courseCode')}"

    def test_course_name_not_all_caps(self):
        """_normalize_name should title-case all-caps names."""
        courses = load_courses(DATA_PATH)
        all_caps_count = 0
        for course in courses:
            raw = course.get("courseName", "")
            if raw and raw == raw.upper() and len(raw) > 4:
                all_caps_count += 1
                s = summarize_course(course)
                assert s["courseName"] != s["courseName"].upper(), \
                    f"All-caps name not normalized: {s['courseName']!r}"
        # Sanity check that we actually tested some
        assert all_caps_count > 0, "No all-caps course names found in data — test may be stale"

    def test_available_seats_format(self):
        """availableSeats must be 'N out of M', 'N', or None."""
        courses = load_courses(DATA_PATH)
        pattern = re.compile(r'^\d+ out of \d+$|^\d+$')
        for course in courses:
            s = summarize_course(course)
            seats = s["availableSeats"]
            if seats is not None:
                assert pattern.match(str(seats)), \
                    f"Unexpected availableSeats format: {seats!r} in {course.get('courseCode')}"

    def test_date_fields_are_iso_or_none(self):
        iso_re = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        courses = load_courses(DATA_PATH)
        for course in courses:
            s = summarize_course(course)
            for field in ("startDate", "endDate"):
                val = s.get(field)
                if val is not None:
                    assert iso_re.match(val), \
                        f"{field}={val!r} is not ISO format in {course.get('courseCode')}"

    def test_units_is_numeric_or_none(self):
        courses = load_courses(DATA_PATH)
        for course in courses:
            s = summarize_course(course)
            u = s["units"]
            if u is not None:
                assert isinstance(u, (int, float)), \
                    f"units is not numeric: {u!r} in {course.get('courseCode')}"
                assert 0 < u <= 20, f"units out of range: {u} in {course.get('courseCode')}"

    def test_delivery_method_values(self):
        """deliveryMethod must be one of the known values or None."""
        known = {"Online - Asynchronous", "Online - Synchronous", None}
        courses = load_courses(DATA_PATH)
        unexpected = set()
        for course in courses:
            s = summarize_course(course)
            dm = s["deliveryMethod"]
            if dm not in known:
                unexpected.add(dm)
        assert not unexpected, f"Unexpected deliveryMethod values: {unexpected}"

    def test_no_internal_fields_leaked(self):
        """Fields like cid, crn, section should NOT appear in summarize output."""
        internal = {"cid", "crn", "section", "term", "filterApplied", "visible", "seatCountUpdatedAt"}
        courses = load_courses(DATA_PATH)
        for course in courses:
            s = summarize_course(course)
            leaked = internal & set(s.keys())
            assert not leaked, f"Internal fields leaked into summary: {leaked}"


# ── Layer 2: Live API card shape ──────────────────────────────────────────────

class TestLiveAPICards:

    @pytest.fixture(scope="class")
    def math_cards(self):
        return api_chat("show me math courses")["courses"]

    @pytest.fixture(scope="class")
    def ge_cards(self):
        return api_chat("show me courses for IGETC area 4")["courses"]

    def test_cards_returned(self, math_cards):
        assert len(math_cards) > 0

    def test_card_required_fields(self, math_cards):
        required = {"courseCode", "courseName", "teachingCollege", "units",
                    "deliveryMethod", "startDate", "availableSeats",
                    "professors", "geChips", "courseNotes"}
        for card in math_cards:
            missing = required - set(card.keys())
            assert not missing, f"API card missing fields: {missing}"

    def test_course_name_not_empty(self, math_cards):
        for card in math_cards:
            assert card["courseName"], f"Empty courseName in card: {card}"

    def test_college_not_empty(self, math_cards):
        for card in math_cards:
            assert card["teachingCollege"], f"Empty teachingCollege in card: {card}"

    def test_start_date_iso(self, math_cards):
        iso_re = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        for card in math_cards:
            if card.get("startDate"):
                assert iso_re.match(card["startDate"]), \
                    f"startDate not ISO: {card['startDate']!r}"

    def test_ge_chips_format(self, ge_cards):
        assert len(ge_cards) > 0
        chips_with_ge = [c for c in ge_cards if c.get("geChips")]
        assert len(chips_with_ge) > 0, "No GE chips on any card"
        for card in chips_with_ge:
            for chip in card["geChips"]:
                assert re.match(r'^(CSU|IGETC|Cal-GETC)\s+\S+', chip), \
                    f"Malformed GE chip: {chip!r}"

    def test_no_all_caps_course_names(self, math_cards):
        for card in math_cards:
            name = card["courseName"]
            if name and len(name) > 4:
                assert name != name.upper(), f"All-caps course name in API response: {name!r}"

    def test_available_seats_parseable(self, math_cards):
        pattern = re.compile(r'^\d+ out of \d+$|^\d+$')
        for card in math_cards:
            seats = card.get("availableSeats")
            if seats is not None:
                assert pattern.match(str(seats)), \
                    f"availableSeats not parseable: {seats!r}"

    def test_no_duplicate_cards(self, math_cards):
        keys = [
            f"{c['courseCode']}|{c['teachingCollege']}|{c.get('professors','')}|{c.get('startDate','')}"
            for c in math_cards
        ]
        assert len(keys) == len(set(keys)), f"Duplicate course cards returned: {keys}"


# ── Layer 3: Frontend mapping simulation ─────────────────────────────────────

class TestFrontendMapping:
    """Simulate apiCourseToCourseCard() in Python to catch mapping bugs."""

    @pytest.fixture(scope="class")
    def raw_cards(self):
        return api_chat("show me async biology courses")["courses"]

    def test_index_sequential(self, raw_cards):
        assert len(raw_cards) > 0
        cards = [api_course_to_card(c, i + 1) for i, c in enumerate(raw_cards)]
        for i, card in enumerate(cards):
            assert card["index"] == i + 1

    def test_date_renders_human_readable(self, raw_cards):
        cards = [api_course_to_card(c, i + 1) for i, c in enumerate(raw_cards)]
        for card in cards:
            if card["startDate"]:
                # Should be "Mon D, YYYY" format
                assert re.match(r'^[A-Z][a-z]{2} \d{1,2}, \d{4}$', card["startDate"]), \
                    f"startDate not human-readable after fmtDate: {card['startDate']!r}"

    def test_seats_parsed_to_int(self, raw_cards):
        cards = [api_course_to_card(c, i + 1) for i, c in enumerate(raw_cards)]
        for card in cards:
            if card["seatsAvailable"] is not None:
                assert isinstance(card["seatsAvailable"], int)
                assert card["seatsAvailable"] >= 0
            if card["seatsTotal"] is not None:
                assert isinstance(card["seatsTotal"], int)
                assert card["seatsTotal"] > 0
                if card["seatsAvailable"] is not None:
                    assert card["seatsAvailable"] <= card["seatsTotal"], \
                        f"Available seats > total: {card['seatsAvailable']} > {card['seatsTotal']}"

    def test_ge_chips_list(self, raw_cards):
        cards = [api_course_to_card(c, i + 1) for i, c in enumerate(raw_cards)]
        for card in cards:
            assert isinstance(card["ge"], list)

    def test_delivery_chip_detection(self, raw_cards):
        """async/sync chip detection logic (mirrors CourseCard.jsx)."""
        cards = [api_course_to_card(c, i + 1) for i, c in enumerate(raw_cards)]
        for card in cards:
            delivery = card["delivery"].lower()
            is_async = "async" in delivery
            is_sync = not is_async and "sync" in delivery
            # Since we searched for async, all results should be async
            assert is_async, \
                f"Non-async delivery in async search results: {card['delivery']!r}"

    def test_no_name_truncation(self, raw_cards):
        """courseName field must pass through without truncation."""
        for raw, card in zip(raw_cards, [api_course_to_card(c, i+1) for i,c in enumerate(raw_cards)]):
            assert card["name"] == (raw.get("courseName") or ""), \
                f"courseName mismatch: raw={raw.get('courseName')!r} card={card['name']!r}"

    def test_units_numeric(self, raw_cards):
        cards = [api_course_to_card(c, i + 1) for i, c in enumerate(raw_cards)]
        for card in cards:
            if card["units"] is not None:
                assert isinstance(card["units"], (int, float)), \
                    f"units not numeric after mapping: {card['units']!r}"
                assert 0 < card["units"] <= 20
