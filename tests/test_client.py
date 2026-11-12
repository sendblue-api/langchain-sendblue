import json

import httpx
import pytest

from langchain_sendblue.client import SendblueClient, SendblueError


def client(handler):
    return SendblueClient(
        "test-key", "test-secret", transport=httpx.MockTransport(handler)
    )


def test_send():
    calls = []

    def handle(request):
        calls.append(request)
        assert request.url == "https://api.sendblue.co/api/send-message"
        assert request.headers["sb-api-key-id"] == "test-key"
        assert request.headers["sb-api-secret-key"] == "test-secret"
        assert json.loads(request.content) == {
            "number": "+15555550123",
            "content": "Hello",
            "from_number": "+15555550124",
        }
        return httpx.Response(
            200, json={"message_handle": "test-message", "status": "QUEUED"}
        )

    assert (
        client(handle).send_message("+15555550123", "Hello", "+15555550124")["status"]
        == "QUEUED"
    )
    assert len(calls) == 1


def test_timeout_not_retried():
    calls = []

    def handle(request):
        calls.append(request)
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(SendblueError, match="check message history"):
        client(handle).send_message("+15555550123", "Hello")
    assert len(calls) == 1


def test_invalid_recipient_does_not_send():
    with pytest.raises(ValueError, match="E.164"):
        client(lambda r: pytest.fail("network should not run")).send_message(
            "bad", "Hello"
        )


def test_list_filters_and_status_encoding():
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"messages": [], "pagination": {"total": 0}})

    api = client(handle)
    result = api.list_messages(20, "+15555550123", 40)
    assert result["pagination"] == {"total": 0}
    assert dict(calls[0].url.params) == {
        "limit": "20",
        "offset": "40",
        "number": "+15555550123",
    }
    api.get_message_status("a&b")
    assert calls[1].url.params["handle"] == "a&b"


@pytest.mark.parametrize("limit", [0, 101, -1, True, 1.5])
def test_bounded_history(limit):
    with pytest.raises(ValueError):
        client(lambda r: pytest.fail("no request")).list_messages(limit)


def test_errors_do_not_leak_credentials_or_body():
    api = client(lambda r: httpx.Response(401, text="test-secret"))
    with pytest.raises(SendblueError) as exc:
        api.list_lines()
    assert str(exc.value) == "Sendblue returned HTTP 401"
