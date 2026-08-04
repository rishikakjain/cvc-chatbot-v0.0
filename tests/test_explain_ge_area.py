"""
Unit tests for explain_ge_area.
"""

from tools.explain_ge_area import explain_ge_area


def test_exact_code_b2():
    result = explain_ge_area("B2")
    assert result["matched"] is True
    assert "Life Science" in result["title"]
    assert "B2" in result["codes"]


def test_exact_code_case_insensitive():
    result = explain_ge_area("b2")
    assert result["matched"] is True
    assert "B2" in result["codes"]


def test_igetc_code_5b():
    result = explain_ge_area("5B")
    assert result["matched"] is True
    assert "5B" in result["codes"]


def test_plain_language_lab():
    result = explain_ge_area("science with a lab")
    assert result["matched"] is True
    assert "B3" in result["codes"]


def test_plain_language_english_comp():
    result = explain_ge_area("english composition")
    assert result["matched"] is True
    assert "A2" in result["codes"]


def test_plain_language_math():
    result = explain_ge_area("math requirement")
    assert result["matched"] is True
    assert "B4" in result["codes"]


def test_framework_igetc():
    result = explain_ge_area("what is IGETC?")
    assert result["matched"] is True
    assert "IGETC" in result["description"]


def test_framework_csu_breadth():
    result = explain_ge_area("CSU breadth")
    assert result["matched"] is True
    assert "CSU" in result["description"]


def test_framework_cal_getc():
    result = explain_ge_area("Cal-GETC")
    assert result["matched"] is True
    assert "Cal-GETC" in result["description"]


def test_unknown_code_returns_unmatched():
    result = explain_ge_area("Z99")
    assert result["matched"] is False
    assert result["codes"] == []


def test_all_csu_breadth_codes_match():
    for code in ["A1", "A2", "A3", "B1", "B2", "B3", "B4", "C1", "C2", "D", "E", "F"]:
        result = explain_ge_area(code)
        assert result["matched"] is True, f"Expected match for {code}"
        assert len(result["description"]) > 20
