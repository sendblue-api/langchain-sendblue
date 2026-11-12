"""Narrow Sendblue HTTP client. No automatic retry of side-effecting calls."""

import re
from typing import Any

import httpx

BASE_URL = "https://api.sendblue.co"


class SendblueError(RuntimeError):
    pass


class SendblueClient:
    def __init__(self, api_key: str, api_secret: str, *, transport=None):
        if not api_key or not api_secret:
            raise ValueError("Both Sendblue API key and API secret are required")
        self._headers = {"sb-api-key-id": api_key, "sb-api-secret-key": api_secret}
        self._transport = transport

    def request(self, method: str, path: str, *, params=None, body=None) -> Any:
        with httpx.Client(
            headers=self._headers,
            transport=self._transport,
            timeout=30,
            follow_redirects=False,
        ) as client:
            try:
                response = client.request(
                    method, BASE_URL + path, params=params, json=body
                )
            except httpx.RequestError as exc:
                raise SendblueError(
                    "Sendblue request failed; check message history before retrying a send"
                ) from exc
            if not response.is_success:
                # Do not expose request headers, secrets, or response content in error messages.
                raise SendblueError(f"Sendblue returned HTTP {response.status_code}")
            try:
                return response.json()
            except ValueError as exc:
                raise SendblueError(
                    "Sendblue returned an invalid JSON response"
                ) from exc

    def send_message(self, number: str, content: str, from_number: str = "") -> Any:
        if not re.fullmatch(r"\+[1-9]\d{7,14}", number):
            raise ValueError("Recipient must use E.164 format")
        if from_number and not re.fullmatch(r"\+[1-9]\d{7,14}", from_number):
            raise ValueError("Sending line must use E.164 format")
        if not content.strip():
            raise ValueError("Message text is required")
        return self.request(
            "POST",
            "/api/send-message",
            body={
                "number": number,
                "content": content,
                **({"from_number": from_number} if from_number else {}),
            },
        )

    def list_messages(self, limit: int = 20, number: str = "", offset: int = 0) -> Any:
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= 100
        ):
            raise ValueError("Limit must be between 1 and 100")
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("Offset must be a non-negative integer")
        return self.request(
            "GET",
            "/api/v2/messages",
            params={
                "limit": limit,
                "offset": offset,
                **({"number": number} if number else {}),
            },
        )

    def get_message_status(self, handle: str) -> Any:
        if not handle.strip():
            raise ValueError("Message handle is required")
        return self.request("GET", "/api/status", params={"handle": handle})

    def list_lines(self) -> Any:
        return self.request("GET", "/api/v2/lines/state")
