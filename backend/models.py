from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class SourceType(Enum):
    DISCORD = "discord"
    NOTION = "notion"


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
    similarity_top_k: Optional[int] = 5
    response_type: Optional[str] = "llm"  # "llm" or "retrieval"
    serverId: str


class FormattedSource(BaseModel):
    channel: str
    sender: Optional[str]
    senderId: Optional[str]
    content: str
    channelId: str
    messageId: str


class NotionPageData(BaseModel):
    title: str
    content: str  # Markdown-formatted content from all blocks
    author: str


class NotionPageMetadata(BaseModel):
    pageId: str
    authorId: str
    createdTime: datetime
    lastEditedTime: datetime
    url: Optional[str] = None


class NotionPageJson(BaseModel):
    data: NotionPageData
    metadata: NotionPageMetadata
