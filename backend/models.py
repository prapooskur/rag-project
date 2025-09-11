from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MessageData(BaseModel):
    senderNickname: Optional[str]
    senderUsername: str
    channelName: str
    content: str


class MessageMetadata(BaseModel):
    messageId: str
    channelId: str
    senderId: str
    serverId: str
    dateTime: datetime  # Automatically handles ISO string parsing/serialization


class MessageJson(BaseModel):
    data: MessageData
    metadata: MessageMetadata


class QueryRequest(BaseModel):
    query: str
    similarity_top_k: Optional[int] = 7
    response_type: Optional[str] = "llm"  # "llm" or "retrieval"
    serverId: str


class FormattedSource(BaseModel):
    channel: str
    sender: Optional[str]
    senderId: Optional[str]
    content: str
    channelId: str
    messageId: str
