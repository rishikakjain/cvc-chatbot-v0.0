"""
End-to-end tests against the live API Gateway.

Covers:
  - Subject keyword search → returns course cards
  - GE area search → returns course cards with matching GE chips
  - Async filter → all returned courses are async
  - Home college exclusion → home college absent from results
  - Multi-turn session continuity → session_id preserved across turns
  - GE explanation (no courses) → text reply, empty courses list
  - FAQ answer (no courses) → text reply, empty courses list
  - Off-topic guardrail → blocked reply, empty courses list
  - Response shape → required fields always present

Run:
    python3 -m pytest tests/test_e2e_api.py -v

Requires: requests  (pip install requests)
"""

import time
import uuid
import pytest
import requests

API_URL = "https://9koj0054n8.execute-api.us-west-2.amazonaws.com/chat"
TIMEOUT = 30  # seconds per request


def chat(message: str, session_id: str | None = None, new_session: bool = False) -> dict:
    sid = session_id or (str(uuid.uuid4()) if new_session else "e2e-test-shared")
    headers = {"Content-Type": "application/json", "X-Session-Id": sid}
    resp = requests.post(API_URL, json={"message": message}, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    data["_session_id_sent"] = sid
    return data


# ── Response shape ────────────────────────────────────────────────────────────

class TestResponseShape:
    def test_required_fields_present(self):
        data = chat("hello", new_session=True)
        assert "reply" in data
        assert "courses" in data
        assert "session_id" in data
        assert "turn_count" in data
        assert isinstance(data["courses"], list)
        assert isinstance(data["reply"], str)
        assert len(data["reply"]) > 0

    def test_turn_count_increments(self):
        sid = str(uuid.uuid4())
        r1 = chat("hi", session_id=sid)
        r2 = chat("show me math courses", session_id=sid)
        assert r2["turn_count"] == r1["turn_count"] + 1

    def test_session_id_echoed(self):
        sid = str(uuid.uuid4())
        data = chat("hello", session_id=sid)
        assert data["session_id"] == sid


# ── Course search ─────────────────────────────────────────────────────────────

class TestCourseSearch:
    def test_math_keyword_returns_cards(self):
        data = chat("show me math courses", new_session=True)
        assert len(data["courses"]) > 0, "Expected course cards for math query"

    def test_biology_keyword_returns_cards(self):
        data = chat("find biology classes", new_session=True)
        assert len(data["courses"]) > 0, "Expected course cards for biology query"

    def test_course_card_has_required_fields(self):
        data = chat("show me math courses", new_session=True)
        assert len(data["courses"]) > 0
        card = data["courses"][0]
        assert "courseName" in card
        assert "teachingCollege" in card
        # courseName should not be all-caps
        name = card["courseName"] or ""
        assert name != name.upper() or len(name) <= 4, f"Course name is all-caps: {name}"

    def test_no_table_rows_in_reply(self):
        data = chat("show me history courses", new_session=True)
        # Markdown table rows start with |
        for line in data["reply"].splitlines():
            assert not line.strip().startswith("|"), f"Table row found in reply: {line}"

    def test_no_bullet_course_list_in_reply(self):
        data = chat("show me psychology courses", new_session=True)
        if len(data["courses"]) > 0:
            # Reply should not re-list courses as bullets
            bullet_course_lines = [
                l for l in data["reply"].splitlines()
                if l.strip().startswith(("- ", "* ", "• ")) and any(
                    c["courseName"] and c["courseName"][:10] in l
                    for c in data["courses"]
                )
            ]
            assert len(bullet_course_lines) == 0, f"Courses re-listed in prose: {bullet_course_lines}"

    def test_date_format_in_cards(self):
        data = chat("show me math courses", new_session=True)
        for card in data["courses"]:
            start = card.get("startDate")
            if start:
                # API returns ISO format (YYYY-MM-DD); frontend formats for display
                import re
                assert re.match(r'^\d{4}-\d{2}-\d{2}$', start), \
                    f"startDate should be ISO YYYY-MM-DD from API, got: {start}"


# ── GE area search ────────────────────────────────────────────────────────────

class TestGESearch:
    def test_ge_area_returns_cards(self):
        data = chat("show me courses that satisfy IGETC area 4", new_session=True)
        assert len(data["courses"]) > 0, "Expected courses for IGETC area 4"

    def test_ge_chips_present_on_cards(self):
        data = chat("find courses for CSU B4", new_session=True)
        assert len(data["courses"]) > 0
        # At least some cards should have GE chips
        cards_with_ge = [c for c in data["courses"] if c.get("geChips")]
        assert len(cards_with_ge) > 0, "Expected GE chips on returned courses"

    def test_ge_explanation_no_cards(self):
        data = chat("what is IGETC area 2?", new_session=True)
        assert isinstance(data["courses"], list)
        # GE explanation should NOT return course cards
        assert len(data["courses"]) == 0, \
            f"Expected no cards for GE explanation, got {len(data['courses'])}"
        assert len(data["reply"]) > 50, "Expected substantive GE explanation"


# ── Delivery method filter ────────────────────────────────────────────────────

class TestDeliveryFilter:
    def test_async_filter_all_async(self):
        data = chat("show me async math courses", new_session=True)
        assert len(data["courses"]) > 0
        for card in data["courses"]:
            delivery = (card.get("deliveryMethod") or "").lower()
            assert "async" in delivery, \
                f"Non-async course in async results: {card.get('courseName')} — {delivery}"


# ── Home college exclusion ────────────────────────────────────────────────────

class TestHomeCollegeExclusion:
    def test_home_college_excluded_from_results(self):
        sid = str(uuid.uuid4())
        # Establish home college
        chat("I go to Cuesta College", session_id=sid)
        time.sleep(1)
        data = chat("show me math courses", session_id=sid)
        assert len(data["courses"]) > 0
        colleges = [c.get("teachingCollege", "") for c in data["courses"]]
        for college in colleges:
            assert "cuesta" not in college.lower(), \
                f"Home college Cuesta appeared in results: {colleges}"

    def test_home_college_stored_in_session(self):
        sid = str(uuid.uuid4())
        data = chat("I go to Victor Valley College", session_id=sid)
        assert data.get("home_college") is not None
        assert "victor" in (data["home_college"] or "").lower()

    def test_abbreviated_college_resolves(self):
        sid = str(uuid.uuid4())
        data = chat("I go to cuesta", session_id=sid)
        hc = (data.get("home_college") or "").lower()
        assert "cuesta" in hc, f"Abbreviated college not resolved: {data.get('home_college')}"


# ── Multi-turn session ────────────────────────────────────────────────────────

class TestMultiTurn:
    def test_session_remembers_home_college(self):
        sid = str(uuid.uuid4())
        chat("I go to Cuesta College", session_id=sid)
        time.sleep(1)
        r2 = chat("show me biology courses", session_id=sid)
        # Home college should persist
        assert r2.get("home_college") is not None
        assert "cuesta" in (r2["home_college"] or "").lower()

    def test_different_sessions_are_independent(self):
        sid1 = str(uuid.uuid4())
        sid2 = str(uuid.uuid4())
        chat("I go to Cuesta College", session_id=sid1)
        time.sleep(1)
        r2 = chat("show me math courses", session_id=sid2)
        # sid2 never told us a home college
        assert r2.get("home_college") is None


# ── FAQ ───────────────────────────────────────────────────────────────────────

class TestFAQ:
    def test_faq_no_cards(self):
        data = chat("how much does CVC cost?", new_session=True)
        assert len(data["courses"]) == 0, "FAQ answer should not return course cards"
        assert len(data["reply"]) > 20

    def test_enrollment_question(self):
        data = chat("how do I enroll in a CVC course?", new_session=True)
        assert len(data["reply"]) > 20
        assert len(data["courses"]) == 0


# ── Guardrail ─────────────────────────────────────────────────────────────────

class TestGuardrail:
    BLOCKED_SIGNAL = "cvc course advising"

    def test_essay_blocked(self):
        data = chat("write me an essay about climate change", new_session=True)
        assert len(data["courses"]) == 0
        assert self.BLOCKED_SIGNAL in data["reply"].lower(), \
            f"Expected guardrail block message, got: {data['reply'][:100]}"

    def test_poem_blocked(self):
        data = chat("write a poem about flowers", new_session=True)
        assert len(data["courses"]) == 0
        assert self.BLOCKED_SIGNAL in data["reply"].lower()

    def test_trivia_blocked(self):
        data = chat("what is the capital of France?", new_session=True)
        assert len(data["courses"]) == 0
        assert self.BLOCKED_SIGNAL in data["reply"].lower()

    def test_on_topic_not_blocked(self):
        data = chat("show me async history courses", new_session=True)
        # Must NOT be blocked — should return courses or a normal reply
        assert self.BLOCKED_SIGNAL not in data["reply"].lower(), \
            "On-topic query was incorrectly blocked by guardrail"
