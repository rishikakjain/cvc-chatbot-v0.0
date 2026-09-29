"""
Tests for _has_in_person_requirement() grounded in actual course note patterns
found in the Victor Valley College and Cuesta College data.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.filter_courses import _has_in_person_requirement


def course(notes):
    return {"courseNotes": notes}


# ── True positives: notes that DO indicate an in-person requirement ──────────

class TestTruePositives:
    def test_proctored_in_person_midterm_and_final(self):
        """Victor Valley MATH 132 pattern — the most common flagged note."""
        c = course(
            "This class will have a proctored, in-person midterm during week 8 "
            "and a proctored, in-person final during week 16. Time and location "
            "will be arranged with the instructor. 3.37 HRS BY ARR"
        )
        assert _has_in_person_requirement(c) is True

    def test_proctored_midterm_early_final(self):
        """MATH 104 variant — midterm week 4, final week 8."""
        c = course(
            "This class will have a proctored, in-person midterm during week 4 "
            "and a proctored, in-person final during week 8. Time and location "
            "will be arranged with the instructor. 9 HRS/WK ARR. Zero Textbook Cost (ZTC)"
        )
        assert _has_in_person_requirement(c) is True

    def test_chem_lab_with_proctored_exams(self):
        """CHEM 100 — lab hours by arrangement PLUS proctored in-person exams."""
        c = course(
            "3.37 lecture hours & 3.37 lab hours weekly by arrangement. "
            "This class will have a proctored, in-person midterm during week 8 "
            "and a proctored, in-person final during week 16. Time and location "
            "will be announced."
        )
        assert _has_in_person_requirement(c) is True

    def test_semicolons_in_notes(self):
        """STATC 1000 — note has semicolons breaking up the sentence."""
        c = course(
            "This class will; have a proctored, in-person midterm during week 8 "
            "and a; proctored, in-person final during week 16. Time and location "
            "will; be arranged with the instructor. 4.5 HRS/WK ARR."
        )
        assert _has_in_person_requirement(c) is True

    def test_final_exam_wording(self):
        """MATH 105 — uses 'final exam' instead of just 'final'."""
        c = course(
            "4.5 HRS/WK by arrangement. This class will have a proctored, "
            "in-person midterm during Week 8 and a proctored, in-person final "
            "exam during Week 16. The time and location will be arranged with "
            "the instructor."
        )
        assert _has_in_person_requirement(c) is True

    def test_testing_center(self):
        c = course("Exams must be taken at the Testing Center on campus.")
        assert _has_in_person_requirement(c) is True

    def test_must_attend_in_person(self):
        c = course("Students must attend in-person for the orientation session.")
        assert _has_in_person_requirement(c) is True

    def test_on_campus_orientation(self):
        c = course("There will be an on-campus orientation during the first week.")
        assert _has_in_person_requirement(c) is True

    def test_required_attendance(self):
        c = course("Required attendance at Saturday lab sessions.")
        assert _has_in_person_requirement(c) is True

    def test_on_site_requirement(self):
        c = course("Lab work is completed on-site at the college science building.")
        assert _has_in_person_requirement(c) is True


# ── True negatives: notes that should NOT be flagged ────────────────────────

class TestTrueNegatives:
    def test_online_lab_hours_by_arrangement(self):
        """Most common Victor Valley pattern — 'lab' just means scheduled online hours."""
        c = course("THIS CLASS WILL UTILIZE MULTIPLE WEBSITES 6.75 WKLY HRS BY ARR "
                   "FOR LECTURE. 6.75 WKLY HRS BY ARR FOR LAB. Low Textbook Cost (LTC)")
        assert _has_in_person_requirement(c) is False

    def test_lab_hours_only_no_in_person(self):
        c = course("3.375 LEC HRS WKLY BY ARR & 3.375 LAB HRS WKLY BY ARR.")
        assert _has_in_person_requirement(c) is False

    def test_lab_hours_with_ztc(self):
        c = course("3.37 lecture hours & 3.37 lab hours weekly by arrangement. "
                   "Zero Textbook Cost (ZTC)")
        assert _has_in_person_requirement(c) is False

    def test_ged_exam_reference_in_spanish(self):
        """BSNC 502 — mentions 'examen de GED' (external exam), not in-person class requirement."""
        c = course(
            "Section 75292 will be taught in Spanish. Esta clase prepara los "
            "estudiantes para aprobar las pruebas de Razonamiento y el examen de GED."
        )
        assert _has_in_person_requirement(c) is False

    def test_empty_notes(self):
        assert _has_in_person_requirement(course("")) is False

    def test_none_notes(self):
        assert _has_in_person_requirement({"courseNotes": None}) is False

    def test_no_notes_key(self):
        assert _has_in_person_requirement({}) is False

    def test_fully_online_note(self):
        c = course("This is a fully online asynchronous course. No campus visits required.")
        assert _has_in_person_requirement(c) is False

    def test_ztc_only_note(self):
        c = course("Zero Textbook Cost (ZTC). All materials provided online.")
        assert _has_in_person_requirement(c) is False


# ── Negation wins: explicit 'no in-person' overrides positive signals ────────

class TestNegationWins:
    def test_no_in_person_beats_in_person_phrase(self):
        """Negation in the note should suppress the in-person signal."""
        c = course("No in-person meetings required. All work is done online.")
        assert _has_in_person_requirement(c) is False

    def test_no_mandatory_in_person(self):
        c = course("No mandatory in-person sessions. Optional in-person help sessions available.")
        assert _has_in_person_requirement(c) is False

    def test_negation_beats_generic_in_person_phrase(self):
        c = course("This course has no in-person components.")
        assert _has_in_person_requirement(c) is False


# ── Real data regression: count matches against full dataset ─────────────────

def test_in_person_count_against_full_dataset():
    """Regression: should detect exactly 26 in-person courses in current data."""
    import json
    from pathlib import Path
    data_path = Path(__file__).parent.parent / "data" / "courses.json"
    with open(data_path) as f:
        courses = json.load(f)
    flagged = [c for c in courses if _has_in_person_requirement(c)]
    assert len(flagged) == 26, (
        f"Expected 26 in-person courses, got {len(flagged)}. "
        "If the source data changed, update this count."
    )

def test_all_flagged_are_victor_valley():
    """All in-person courses in current data are from Victor Valley College."""
    import json
    from pathlib import Path
    data_path = Path(__file__).parent.parent / "data" / "courses.json"
    with open(data_path) as f:
        courses = json.load(f)
    flagged = [c for c in courses if _has_in_person_requirement(c)]
    colleges = {c["teachingCollege"] for c in flagged}
    assert colleges == {"Victor Valley College"}, (
        f"Unexpected colleges with in-person requirements: {colleges}"
    )

def test_cuesta_courses_all_fully_online():
    """All Cuesta College courses should be fully online (no in-person requirement)."""
    import json
    from pathlib import Path
    data_path = Path(__file__).parent.parent / "data" / "courses.json"
    with open(data_path) as f:
        courses = json.load(f)
    cuesta = [c for c in courses if "cuesta" in c.get("teachingCollege", "").lower()]
    in_person = [c for c in cuesta if _has_in_person_requirement(c)]
    assert in_person == [], (
        f"{len(in_person)} Cuesta courses incorrectly flagged as in-person: "
        + str([c['courseCode'] for c in in_person])
    )
