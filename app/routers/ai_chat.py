from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime, timezone
from app.core.database import get_database
from app.schemas.chat_log import ChatMessageCreate, ChatMessageOut
from app.services.ai_service import build_context, get_ai_reply
from app.utils.bson import serialize_doc

router = APIRouter(prefix="/api/ai-chat", tags=["AI Chat"])

@router.post("/", response_model=ChatMessageOut)
async def send_chat_message(message: ChatMessageCreate):
    db = get_database()
    timestamp = datetime.now(timezone.utc)
    
    # Save user message
    user_msg_doc = {
        "user_id": message.user_id,
        "robot_id": message.robot_id,
        "role": "user",
        "message": message.message,
        "timestamp": timestamp,
        "context_snapshot": None
    }
    await db.ai_chat_logs.insert_one(user_msg_doc)
    
    # Get context and AI reply
    context = await build_context(message.robot_id)
    reply_text = await get_ai_reply(message.message, context)
    
    # Save assistant message
    assistant_msg_doc = {
        "user_id": message.user_id,
        "robot_id": message.robot_id,
        "role": "assistant",
        "message": reply_text,
        "timestamp": datetime.now(timezone.utc),
        "context_snapshot": context
    }
    result = await db.ai_chat_logs.insert_one(assistant_msg_doc)
    assistant_msg_doc["_id"] = result.inserted_id
    
    return ChatMessageOut(**serialize_doc(assistant_msg_doc))

@router.get("/history", response_model=List[ChatMessageOut])
async def get_chat_history(user_id: str, limit: int = 50):
    db = get_database()
    
    cursor = db.ai_chat_logs.find({"user_id": user_id}).sort("timestamp", 1).limit(min(limit, 200))
    logs = await cursor.to_list(length=200)
    
    return [ChatMessageOut(**serialize_doc(log)) for log in logs]
