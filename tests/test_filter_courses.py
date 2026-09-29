"""
Unit tests for filter_courses.
All tests use the real courses.json — no mocking needed since we're testing
filter logic, not the data itself.
"""

import pytest
from pathlib import Path
from tools.filter_courses import filter_courses, load_courses, _courses_cache
import tools.filter_courses as fc_module

DATA_PATH = Path(__file__).parent.parent / "data" / "courses.json"


@pytest.fixture(autouse=True)
def clear_cache():
    fc_module._courses_cache = None
    yield
    fc_module._courses_cache = None


def test_loads_courses():
    courses = load_courses(DATA_PATH)
    assert len(courses) > 800, "Expected 848 courses from 2 colleges"


def test_ge_filter_life_science():
    results = filter_courses(ge_areas=["B2"], source_path=DATA_PATH)
    assert len(results) > 0
    for course in results:
        all_areas = (
            (course.get("csuBreadth") or [])
            + (course.get("igetc") or [])
            + (course.get("calGetc") or [])
        )
        assert "B2" in [a.upper() for a in all_areas], f"{course['courseCode']} missing B2"


def test_ge_filter_science_with_lab():
    # B1 (physical science) + B3 (lab) — any match
    results = filter_courses(ge_areas=["B1", "B3"], source_path=DATA_PATH)
    assert len(results) > 0
    for course in results:
        all_areas = (
            (course.get("csuBreadth") or [])
            + (course.get("igetc") or [])
            + (course.get("calGetc") or [])
        )
        upper = [a.upper() for a in all_areas]
        assert "B1" in upper or "B3" in upper


def test_exclude_home_college():
    results = filter_courses(
        exclude_college="Victor Valley College",
        source_path=DATA_PATH,
    )
    assert all(c["teachingCollege"] != "Victor Valley College" for c in results)


def test_exclude_home_college_case_insensitive():
    results = filter_courses(
        exclude_college="victor valley college",
        source_path=DATA_PATH,
    )
    assert all(c["teachingCollege"] != "Victor Valley College" for c in results)


def test_has_seats_filter():
    results = filter_courses(has_seats=True, source_path=DATA_PATH)
    assert all((c.get("seatsAvailable") or 0) > 0 for c in results)


def test_async_delivery_filter():
    results = filter_courses(delivery_method="async", top_n=20, source_path=DATA_PATH)
    assert len(results) > 0
    for course in results:
        assert "asynchronous" in (course.get("deliveryMethod") or "").lower()


def test_sync_delivery_filter():
    results = filter_courses(delivery_method="sync", top_n=20, source_path=DATA_PATH)
    # Cuesta has synchronous courses
    for course in results:
        assert "synchronous" in (course.get("deliveryMethod") or "").lower()


def test_top_n_limit():
    results = filter_courses(top_n=3, source_path=DATA_PATH)
    assert len(results) <= 3


def test_sorted_by_score_descending():
    from tools.filter_courses import _rank_score
    results = filter_courses(top_n=10, source_path=DATA_PATH)
    scores = [_rank_score(c) for c in results]
    assert scores == sorted(scores, reverse=True)


def test_no_results_returns_empty_list():
    results = filter_courses(
        ge_areas=["B99"],  # nonexistent GE code
        source_path=DATA_PATH,
    )
    assert results == []


def test_english_comp_igetc():
    # IGETC 1A = English Composition
    results = filter_courses(ge_areas=["1A"], source_path=DATA_PATH)
    assert len(results) > 0


def test_combined_filters():
    results = filter_courses(
        ge_areas=["B2", "5B"],
        delivery_method="async",
        exclude_college="Cuesta College",
        has_seats=True,
        top_n=5,
        source_path=DATA_PATH,
    )
    for course in results:
        assert course["teachingCollege"] != "Cuesta College"
        assert "asynchronous" in (course.get("deliveryMethod") or "").lower()
        assert (course.get("seatsAvailable") or 0) > 0
