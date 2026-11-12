import httpx
import pytest
from pydantic import ValidationError

from langchain_sendblue import SendblueToolkit
from langchain_sendblue.client import SendblueClient


def test_read_only_default_and_secrets_excluded():
    toolkit = SendblueToolkit(api_key="test-key", api_secret="test-secret")
    assert len(toolkit.get_tools()) == 3
    assert all(t.metadata["read_only"] for t in toolkit.get_tools())
    assert "test-secret" not in repr(toolkit)
    assert "test-key" not in toolkit.model_dump_json()


def test_structured_send_uses_real_transport_boundary(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"message_handle": "test", "status": "QUEUED"})

    monkeypatch.setattr(
        SendblueToolkit,
        "_client",
        lambda self: SendblueClient(
            "test-key", "test-secret", transport=httpx.MockTransport(handler)
        ),
    )
    toolkit = SendblueToolkit(
        api_key="test-key", api_secret="test-secret", allow_writes=True
    )
    tool = next(t for t in toolkit.get_tools() if t.name == "sendblue_send_message")
    result = tool.invoke(
        {"number": "+15555550123", "content": "Hello", "from_number": "+15555550124"}
    )
    assert result["status"] == "QUEUED"
    assert len(calls) == 1
    with pytest.raises(ValidationError):
        tool.invoke({"number": "bad", "content": "Hello"})
    assert len(calls) == 1


def test_tool_history_schema_rejects_unbounded_limit():
    tool = next(
        t
        for t in SendblueToolkit(
            api_key="test-key", api_secret="test-secret"
        ).get_tools()
        if t.name == "sendblue_list_messages"
    )
    with pytest.raises(ValidationError):
        tool.invoke({"limit": 1000})
