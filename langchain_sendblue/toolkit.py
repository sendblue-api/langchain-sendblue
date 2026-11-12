"""Explicitly opt in to write tools when constructing an agent."""

from langchain_core.tools import BaseTool, BaseToolkit, StructuredTool
from pydantic import BaseModel, Field, SecretStr

from langchain_sendblue.client import SendblueClient


class SendMessageInput(BaseModel):
    number: str = Field(
        description="Recipient phone number in E.164 format",
        pattern=r"^\+[1-9]\d{7,14}$",
    )
    content: str = Field(description="Exact text approved by the user", min_length=1)
    from_number: str = Field(
        default="",
        description="Sending line in E.164 format; required for free shared-line plans",
    )


class ListMessagesInput(BaseModel):
    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum messages in this page"
    )
    number: str = Field(
        default="", description="Optional phone number to filter the conversation"
    )
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class MessageStatusInput(BaseModel):
    handle: str = Field(min_length=1, description="Message handle returned by Sendblue")


class EmptyInput(BaseModel):
    pass


class SendblueToolkit(BaseToolkit):
    """Read Sendblue data, optionally enabling explicit message sends.

    Configure a human approval interrupt for sendblue_send_message in agents.
    """

    api_key: SecretStr = Field(exclude=True, repr=False)
    api_secret: SecretStr = Field(exclude=True, repr=False)
    allow_writes: bool = False

    def _client(self) -> SendblueClient:
        return SendblueClient(
            self.api_key.get_secret_value(), self.api_secret.get_secret_value()
        )

    def get_tools(self) -> list[BaseTool]:
        client = self._client()
        tools: list[BaseTool] = [
            StructuredTool.from_function(
                func=client.list_lines,
                name="sendblue_list_lines",
                args_schema=EmptyInput,
                description="Read sending line state for the connected Sendblue workspace.",
                metadata={"read_only": True},
            ),
            StructuredTool.from_function(
                func=client.list_messages,
                name="sendblue_list_messages",
                args_schema=ListMessagesInput,
                description="Read one bounded page of Sendblue messages. Filter by phone number and use offset for pagination.",
                metadata={"read_only": True},
            ),
            StructuredTool.from_function(
                func=client.get_message_status,
                name="sendblue_get_message_status",
                args_schema=MessageStatusInput,
                description="Read delivery status by the message handle returned when sending.",
                metadata={"read_only": True},
            ),
        ]
        if self.allow_writes:
            tools.append(
                StructuredTool.from_function(
                    func=client.send_message,
                    name="sendblue_send_message",
                    args_schema=SendMessageInput,
                    description="Send one text message only after the user confirms the recipient and exact content. Free plans require from_number. Delivery is asynchronous; do not automatically retry after a timeout. Check message history first.",
                    metadata={"read_only": False, "requires_confirmation": True},
                )
            )
        return tools
