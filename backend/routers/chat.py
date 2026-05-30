import json
import logging
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, Body, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import ChatMessage
from backend.services.agents import stylist_agent, WardrobeDeps
from backend.services.memory import should_consolidate, consolidate_user_memory

logger = logging.getLogger("chat_router")
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message")
async def send_message(
    payload: dict = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_session),
):
    """
    Posts a message to the stylist assistant Aura (powered by PydanticAI + Gemini)
    and returns a JSON response.

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
        logger.warning(f"Failed to persist user message in DB history: {e}")

    # 2. Build message_history for PydanticAI from the conversation_history payload
    #    PydanticAI expects message_history from previous agent.run() calls.
    #    Since we're passing raw user/assistant dicts, we inject them into the prompt
    #    context rather than using PydanticAI's native message_history format.
    #    The dynamic system prompt already includes wardrobe context and style profile.

    # Build a conversational context string from history
    history_context = ""
    if conversation_history:
        history_lines = []
        for msg in conversation_history[-10:]:  # Keep last 10 messages to avoid token bloat
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            history_lines.append(f"{role}: {content}")
        history_context = (
            "\n[RECENT CONVERSATION HISTORY]:\n"
            + "\n".join(history_lines)
            + "\n\n[NEW USER MESSAGE]:\n"
        )

    # 3. Call the PydanticAI stylist agent
    try:
        result = await stylist_agent.run(
            f"{history_context}{user_message}",
            deps=WardrobeDeps(db=db),
        )
        reply_text = result.output
    except Exception as e:
        logger.error(f"Stylist agent error: {e}")
        reply_text = f"I'm having trouble connecting right now. Please try again. (Error: {e})"

    # 4. Save assistant response to database history
    if reply_text:
        try:
            assistant_msg_db = ChatMessage(role="assistant", content=reply_text)
            db.add(assistant_msg_db)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist assistant response in DB history: {e}")

    # 5. Trigger memory consolidation every N messages (async background task)
    if should_consolidate():
        # Build the recent messages list for consolidation
        all_history = conversation_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply_text},
        ]
        background_tasks.add_task(consolidate_user_memory, all_history[-10:], db)

    return {"reply": reply_text}


@router.post("/stream")
async def send_message_stream(
    payload: dict = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_session),
):
    """
    Posts a message to the stylist assistant Aura (powered by PydanticAI + Gemini)
    and returns a Server-Sent Events (SSE) streaming response.

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
        logger.warning(f"Failed to persist user message in DB history: {e}")

    # Build a conversational context string from history
    history_context = ""
    if conversation_history:
        history_lines = []
        for msg in conversation_history[-10:]:  # Keep last 10 messages to avoid token bloat
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            history_lines.append(f"{role}: {content}")
        history_context = (
            "\n[RECENT CONVERSATION HISTORY]:\n"
            + "\n".join(history_lines)
            + "\n\n[NEW USER MESSAGE]:\n"
        )

    # 2. Asynchronous generator for SSE
    async def event_generator():
        reply_chunks = []
        try:
            async with stylist_agent.run_stream(
                f"{history_context}{user_message}",
                deps=WardrobeDeps(db=db),
            ) as result:
                async for chunk in result.stream_text(delta=True):
                    reply_chunks.append(chunk)
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Stylist agent stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Save assistant response to database history once the stream is fully finished
            full_reply = "".join(reply_chunks).strip()
            if full_reply:
                try:
                    assistant_msg_db = ChatMessage(role="assistant", content=full_reply)
                    db.add(assistant_msg_db)
                    db.commit()
                except Exception as e:
                    logger.warning(f"Failed to persist assistant response in DB history: {e}")

                # Trigger memory consolidation every N messages (async background task)
                if should_consolidate():
                    all_history = conversation_history + [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": full_reply},
                    ]
                    background_tasks.add_task(consolidate_user_memory, all_history[-10:], db)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {e}")
