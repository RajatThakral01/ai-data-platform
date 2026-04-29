"""Tests for llm.ollama_client.

These tests mock the Ollama SDK so they run without a live Ollama server.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from llm.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelError,
    OllamaQueryError,
    query_model,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def mock_ollama_client():
    """Patch ``ollama.Client`` so no real server is needed."""
    with patch("llm.ollama_client.ollama.Client") as MockClient:
        instance = MagicMock()
        MockClient.return_value = instance
        yield instance


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------
class TestClientInit:
    def test_default_values(self, mock_ollama_client):
        client = OllamaClient()
        assert client.model == "mistral"
        assert client.host == "http://localhost:11434"
        assert client.temperature == 0.7

    def test_custom_values(self, mock_ollama_client):
        client = OllamaClient(
            model="llama3",
            host="http://192.168.1.10:11434",
            temperature=0.3,
        )
        assert client.model == "llama3"
        assert client.host == "http://192.168.1.10:11434"
        assert client.temperature == 0.3

    def test_repr(self, mock_ollama_client):
        client = OllamaClient()
        r = repr(client)
        assert "mistral" in r
        assert "localhost" in r


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------
class TestHealthChecks:
    def test_is_server_running_true(self, mock_ollama_client):
        mock_ollama_client.list.return_value = SimpleNamespace(models=[])
        client = OllamaClient()
        assert client.is_server_running() is True

    def test_is_server_running_false(self, mock_ollama_client):
        mock_ollama_client.list.side_effect = ConnectionError("refused")
        client = OllamaClient()
        assert client.is_server_running() is False

    def test_is_model_available_true(self, mock_ollama_client):
        mock_ollama_client.list.return_value = SimpleNamespace(
            models=[SimpleNamespace(model="mistral:latest")]
        )
        client = OllamaClient(model="mistral")
        assert client.is_model_available() is True

    def test_is_model_available_false(self, mock_ollama_client):
        mock_ollama_client.list.return_value = SimpleNamespace(
            models=[SimpleNamespace(model="llama3:latest")]
        )
        client = OllamaClient(model="mistral")
        assert client.is_model_available() is False


# ---------------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------------
class TestQuery:
    def _make_response(self, text: str):
        return SimpleNamespace(message=SimpleNamespace(content=text))

    def test_successful_query(self, mock_ollama_client):
        mock_ollama_client.chat.return_value = self._make_response("Hello!")
        client = OllamaClient()
        result = client.query("Hi")
        assert result == "Hello!"

    def test_system_prompt_included(self, mock_ollama_client):
        mock_ollama_client.chat.return_value = self._make_response("OK")
        client = OllamaClient(system_prompt="Be brief.")
        client.query("Hi")

        call_kwargs = mock_ollama_client.chat.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "Be brief."
        assert messages[1]["role"] == "user"

    def test_no_system_prompt(self, mock_ollama_client):
        mock_ollama_client.chat.return_value = self._make_response("OK")
        client = OllamaClient(system_prompt=None)
        client.query("Hi")

        call_kwargs = mock_ollama_client.chat.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_empty_prompt_raises(self, mock_ollama_client):
        client = OllamaClient()
        with pytest.raises(OllamaQueryError, match="empty"):
            client.query("")

    def test_whitespace_prompt_raises(self, mock_ollama_client):
        client = OllamaClient()
        with pytest.raises(OllamaQueryError, match="empty"):
            client.query("   ")

    def test_temperature_override(self, mock_ollama_client):
        mock_ollama_client.chat.return_value = self._make_response("OK")
        client = OllamaClient(temperature=0.7)
        client.query("Hi", temperature=0.1)

        call_kwargs = mock_ollama_client.chat.call_args
        options = call_kwargs.kwargs.get("options") or call_kwargs[1].get("options")
        assert options["temperature"] == 0.1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
class TestErrorHandling:
    def test_connection_refused(self, mock_ollama_client):
        from ollama import RequestError

        mock_ollama_client.chat.side_effect = RequestError("connection refused")
        client = OllamaClient()
        with pytest.raises(OllamaConnectionError, match="running"):
            client.query("Hi")

    def test_model_not_found(self, mock_ollama_client):
        from ollama import ResponseError

        mock_ollama_client.chat.side_effect = ResponseError("model 'xyz' not found")
        client = OllamaClient(model="xyz")
        with pytest.raises(OllamaModelError, match="not available"):
            client.query("Hi")

    def test_generic_response_error(self, mock_ollama_client):
        from ollama import ResponseError

        mock_ollama_client.chat.side_effect = ResponseError("internal error 500")
        client = OllamaClient()
        with pytest.raises(OllamaQueryError, match="error"):
            client.query("Hi")

    def test_connection_error(self, mock_ollama_client):
        mock_ollama_client.chat.side_effect = ConnectionError("refused")
        client = OllamaClient()
        with pytest.raises(OllamaConnectionError, match="refused"):
            client.query("Hi")

    def test_empty_response_raises(self, mock_ollama_client):
        mock_ollama_client.chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content="")
        )
        client = OllamaClient()
        with pytest.raises(OllamaQueryError, match="empty response"):
            client.query("Hi")


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------
class TestQueryModelFunction:
    def test_delegates_to_client(self, mock_ollama_client):
        mock_ollama_client.chat.return_value = SimpleNamespace(
            message=SimpleNamespace(content="response")
        )
        result = query_model("Hello")
        assert result == "response"
