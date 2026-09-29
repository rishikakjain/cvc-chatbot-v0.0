"""
Unit tests for get_faq_answer.
"""

from tools.get_faq_answer import get_faq_answer


def test_enroll_exact():
    result = get_faq_answer("how do i enroll?")
    assert result["matched"] is True
    assert "enroll" in result["answer"].lower()


def test_enroll_alternate_spelling():
    result = get_faq_answer("how do i enrol in a class")
    assert result["matched"] is True


def test_transfer_credit():
    result = get_faq_answer("will this count for transfer?")
    assert result["matched"] is True
    assert "counselor" in result["answer"].lower()


def test_transfer_credit_misspelling():
    result = get_faq_answer("does this tranfer?")
    assert result["matched"] is True


def test_prerequisite():
    result = get_faq_answer("what are the prereqs?")
    assert result["matched"] is True


def test_prereq_alternate():
    result = get_faq_answer("what do i need to take this class")
    assert result["matched"] is True


def test_seats():
    result = get_faq_answer("how many seats are left?")
    assert result["matched"] is True


def test_seats_alternate():
    result = get_faq_answer("is the class full?")
    assert result["matched"] is True


def test_fees():
    result = get_faq_answer("how much does it cost?")
    assert result["matched"] is True


def test_drop():
    result = get_faq_answer("how do i drop a class?")
    assert result["matched"] is True


def test_withdraw_alternate():
    result = get_faq_answer("can i unenroll?")
    assert result["matched"] is True


def test_what_is_cvc():
    result = get_faq_answer("what is cvc")
    assert result["matched"] is True


def test_no_match_returns_fallback():
    result = get_faq_answer("what is the meaning of life")
    assert result["matched"] is False
    assert len(result["answer"]) > 0


def test_async_explanation():
    result = get_faq_answer("what does asynchronous mean?")
    assert result["matched"] is True
    assert "async" in result["answer"].lower()


def test_home_college():
    result = get_faq_answer("what is my home college?")
    assert result["matched"] is True
