import json
import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import ChatMessage
from backend.services.llm_engine import handle_chat_completion

logger = logging.getLogger("chat_router")
router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatPayload:
    message: str
    history: List[Dict[str, str]]

@router.post("/message")
async def send_message(
    payload: dict = Body(...),
    db: Session = Depends(get_session)
):
    """
    Posts a message to the stylist assistant Aura (powered by Gemini) and returns a JSON response.
    Payload schema:
    {
      "message": "User query here",
      "history": [{"role": "user", "content": "..."}, ...]
    }
    """
    user_message = payload.get("message")
    conversation_history = payload.get("history", [])
    
    if not user_message:
        raise HTTPException(status_code=400, detail="Missing required field: 'message'")
        
    # 1. Save user message to database history
    try:
        user_msg_db = ChatMessage(role="user", content=user_message)
        db.add(user_msg_db)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to persist user message in DB history: {str(e)}")

    # 2. Generate fashion assistant response via Gemini text context completion (no CLIP model used)
    reply_text = await handle_chat_completion(user_message, conversation_history, db)

    # 3. Save assistant response to database history
    if reply_text:
        try:
            assistant_msg_db = ChatMessage(role="assistant", content=reply_text)
            db.add(assistant_msg_db)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist assistant response in DB history: {str(e)}")

    return {"reply": reply_text}

@router.get("/history", response_model=List[ChatMessage])
async def get_chat_history(db: Session = Depends(get_session)):
    """Retrieves full conversation logs from database sorted chronologically."""
    statement = select(ChatMessage).order_by(ChatMessage.timestamp.asc())
    results = db.exec(statement).all()
    return results

@router.delete("/history")
async def clear_chat_history(db: Session = Depends(get_session)):
    """Deletes all messages in conversation history."""
    try:
        statement = select(ChatMessage)
        results = db.exec(statement).all()
        for msg in results:
            db.delete(msg)
        db.commit()
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")
