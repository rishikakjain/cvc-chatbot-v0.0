"""
Tests that verify the SQLite backend loads and serves the same data
as the JSON fallback path.
"""
from pathlib import Path
import tools.filter_courses as fc_module
from tools.filter_courses import filter_courses, _is_ztc
from data.college_regions import get_college_region, CA_REGIONS

DB_PATH = Path(__file__).parent.parent / "data" / "courses.db"
JSON_PATH = Path(__file__).parent.parent / "data" / "courses.json"


def _reset():
    fc_module._courses_cache = None


def test_sqlite_loads():
    _reset()
    courses = fc_module.load_courses(DB_PATH)
    assert len(courses) >= 848


def test_sqlite_field_types():
    _reset()
    courses = fc_module.load_courses(DB_PATH)
    c = courses[0]
    assert isinstance(c["badges"], list)
    assert isinstance(c["csuBreadth"], list)
    assert isinstance(c["igetc"], list)
    assert isinstance(c["calGetc"], list)
    assert isinstance(c.get("seatsAvailable"), (int, type(None)))
    assert isinstance(c.get("units"), (int, type(None)))


def test_sqlite_same_count_as_json():
    _reset()
    db_courses = fc_module.load_courses(DB_PATH)
    _reset()
    json_courses = fc_module.load_courses(JSON_PATH)
    assert len(db_courses) == len(json_courses)


def test_region_filter_inland_empire():
    _reset()
    results = filter_courses(region="Inland Empire", has_seats=False, top_n=20, source_path=DB_PATH)
    assert len(results) > 0
    for c in results:
        assert get_college_region(c["teachingCollege"].lower()) == "Inland Empire"


def test_region_filter_central_coast():
    _reset()
    results = filter_courses(region="Central Coast", has_seats=False, top_n=20, source_path=DB_PATH)
    assert len(results) > 0
    for c in results:
        assert get_college_region(c["teachingCollege"].lower()) == "Central Coast"


def test_duration_filter_8_weeks():
    _reset()
    from tools.filter_courses import _course_duration_weeks
    results = filter_courses(max_duration_weeks=8, has_seats=False, top_n=50, source_path=DB_PATH)
    for c in results:
        weeks = _course_duration_weeks(c)
        if weeks is not None:
            assert weeks <= 8


def test_condensed_only_backward_compat():
    _reset()
    r1 = filter_courses(condensed_only=True, has_seats=False, top_n=50, source_path=DB_PATH)
    _reset()
    r2 = filter_courses(max_duration_weeks=10, has_seats=False, top_n=50, source_path=DB_PATH)
    assert [c["crn"] for c in r1] == [c["crn"] for c in r2]


def test_ztc_filter_sqlite():
    _reset()
    results = filter_courses(ztc=True, has_seats=False, top_n=100, source_path=DB_PATH)
    assert len(results) >= 10
    for c in results:
        assert _is_ztc(c), f"{c.get('courseCode')} passed ZTC filter but _is_ztc returned False"


def test_college_region_mapping():
    assert get_college_region("Victor Valley College") == "Inland Empire"
    assert get_college_region("Cuesta College") == "Central Coast"
    assert get_college_region("unknown college xyz") == "Other"
    for region in CA_REGIONS:
        assert isinstance(region, str)
