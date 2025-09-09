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
    dateTime: datetime  # Automatically handles ISO string parsing/serialization


class MessageJson(BaseModel):
    data: MessageData
    metadata: MessageMetadata
