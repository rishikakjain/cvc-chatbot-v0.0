"""
Unit tests for the _check_guardrail() function in api/session_handler.py.

These tests mock boto3 entirely — no AWS calls, runs instantly.

Run:
    python3 -m pytest tests/test_guardrail_unit.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
import api.session_handler as handler


@pytest.fixture(autouse=True)
def reset_bedrock_client():
    """Reset the cached boto3 client before each test."""
    handler._bedrock = None
    yield
    handler._bedrock = None


def _mock_bedrock(action: str) -> MagicMock:
    """Return a mock bedrock client whose apply_guardrail returns the given action."""
    mock_client = MagicMock()
    mock_client.apply_guardrail.return_value = {"action": action}
    return mock_client


class TestCheckGuardrail:

    def test_no_guardrail_id_passes(self, monkeypatch):
        """When GUARDRAIL_ID is unset, all messages pass through (returns False)."""
        monkeypatch.setattr(handler, "GUARDRAIL_ID", None)
        assert handler._check_guardrail("what is 7*8") is False

    def test_empty_guardrail_id_passes(self, monkeypatch):
        """Empty string GUARDRAIL_ID also passes through."""
        monkeypatch.setattr(handler, "GUARDRAIL_ID", "")
        assert handler._check_guardrail("write me a poem") is False

    def test_guardrail_intervened_returns_true(self, monkeypatch):
        """GUARDRAIL_INTERVENED action → True (block the message)."""
        monkeypatch.setattr(handler, "GUARDRAIL_ID", "test-id-123")
        mock_client = _mock_bedrock("GUARDRAIL_INTERVENED")
        with patch.object(handler, "_get_bedrock", return_value=mock_client):
            result = handler._check_guardrail("what is the capital of France?")
        assert result is True
        mock_client.apply_guardrail.assert_called_once_with(
            guardrailIdentifier="test-id-123",
            guardrailVersion="DRAFT",
            source="INPUT",
            content=[{"text": {"text": "what is the capital of France?"}}],
        )

    def test_passthrough_action_returns_false(self, monkeypatch):
        """Any action other than GUARDRAIL_INTERVENED → False (allow through)."""
        monkeypatch.setattr(handler, "GUARDRAIL_ID", "test-id-123")
        mock_client = _mock_bedrock("NONE")
        with patch.object(handler, "_get_bedrock", return_value=mock_client):
            result = handler._check_guardrail("show me math courses")
        assert result is False

    def test_boto3_exception_fails_closed(self, monkeypatch):
        """If apply_guardrail raises, fail closed (returns True) — never pass unknown traffic."""
        monkeypatch.setattr(handler, "GUARDRAIL_ID", "test-id-123")
        mock_client = MagicMock()
        mock_client.apply_guardrail.side_effect = Exception("ResourceNotFoundException")
        with patch.object(handler, "_get_bedrock", return_value=mock_client):
            result = handler._check_guardrail("some message")
        assert result is True

    def test_wrong_account_exception_fails_closed(self, monkeypatch):
        """Cross-account ResourceNotFound also fails closed (reproduces the original bug)."""
        monkeypatch.setattr(handler, "GUARDRAIL_ID", "bqrnqpu8ls2q")  # stale wrong-account ID
        mock_client = MagicMock()
        mock_client.apply_guardrail.side_effect = Exception(
            "An error occurred (ResourceNotFoundException) when calling the ApplyGuardrail operation"
        )
        with patch.object(handler, "_get_bedrock", return_value=mock_client):
            result = handler._check_guardrail("tell me a joke")
        assert result is True  # must NOT be False (the original bug returned False here)
