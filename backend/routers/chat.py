import json
import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import ChatMessage
from backend.services.llm_engine import handle_chat_stream

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
    Posts a message to the stylist assistant and returns a live Server-Sent Events (SSE) stream.
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

    # 2. Define the generator that yields SSE events
    async def sse_event_generator():
        full_response = []
        try:
            async for text_chunk in handle_chat_stream(user_message, conversation_history, db):
                full_response.append(text_chunk)
                # Send text chunk formatted as SSE
                yield f"data: {json.dumps({'text': text_chunk})}\n\n"
                
            # Stream completed successfully - save full response to DB
            full_response_text = "".join(full_response)
            if full_response_text:
                try:
                    assistant_msg_db = ChatMessage(role="assistant", content=full_response_text)
                    db.add(assistant_msg_db)
                    db.commit()
                except Exception as e:
                    logger.warning(f"Failed to persist assistant response in DB history: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error in SSE generator stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
        yield "data: [DONE]\n\n"

    # 3. Return streaming response with correct SSE header
    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Prevents Nginx/proxy buffering
        }
    )

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
