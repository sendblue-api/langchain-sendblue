# langchain-sendblue

Official Sendblue tools for LangChain and LangGraph. Read sending lines, recent messages, and delivery status; optionally enable one-to-one text sending.

## Install

```sh
pip install langchain-sendblue
```

Package version 0.1.0 is pending its first PyPI publication. Source installation is available with `pip install .`.

## Setup

Create an API key and secret in your [Sendblue dashboard](https://app.sendblue.com/). Store them in your environment or secret manager.

```python
import os
from langchain_sendblue import SendblueToolkit

toolkit = SendblueToolkit(
    api_key=os.environ["SENDBLUE_API_KEY"],
    api_secret=os.environ["SENDBLUE_API_SECRET"],
)
tools = toolkit.get_tools()  # Three read-only tools by default.
lines = next(t for t in tools if t.name == "sendblue_list_lines").invoke({})
```

Set `allow_writes=True` to include `sendblue_send_message`. In a LangGraph agent, add a human approval interrupt for that tool. Its metadata is descriptive and does not enforce a security boundary: your application is responsible for approval. Confirm both recipient and text before sending. A free shared-line account requires `from_number` and a verified recipient. Account plan limits still apply.

Delivery is asynchronous. Save the returned message handle and query `sendblue_get_message_status`. No automatic send retries are performed. If a request times out, check history before retrying to avoid duplicates.

All API traffic goes to `https://api.sendblue.co` with the key pair in headers. The package implements no telemetry or extra persistence. Tool output can contain message content and phone numbers; send it only to model providers you authorize. See [Sendblue privacy](https://www.sendblue.com/privacy-policy).

## Development

`uv sync` then `uv run pytest`. Tests use a mock HTTP transport and make no real sends. `uv build` creates the source archive and wheel. PyPI publishing uses the repository's GitHub Actions trusted publisher; no permanent token is stored.

[API docs](https://docs.sendblue.com/) · [Source](https://github.com/sendblue-api/langchain-sendblue) · support@sendblue.com
