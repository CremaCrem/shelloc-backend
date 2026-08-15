from pydantic import BaseModel, Field
from typing import Literal, Optional, Any
from datetime import datetime

class ChatMessageCreate(BaseModel):
    user_id: str = Field(..., description="App user identifier")
    robot_id: str = Field(..., description="Used to build context")
    message: str = Field(..., description="The user's question")

class ChatMessageOut(BaseModel):
    id: str = Field(..., description="MongoDB ObjectId as string")
    role: Literal["user", "assistant"] = Field(..., description="Role of the message sender")
    message: str = Field(..., description="The message content")
    timestamp: datetime = Field(..., description="Server-set UTC timestamp")
    context_snapshot: Optional[Any] = Field(None, description="Context snapshot used by the assistant")
