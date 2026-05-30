"""
Asynchronous memory consolidation pipeline.

Triggered every N chat messages (default: 5) to distill style preferences
from recent conversation history and merge them into the UserStyleProfile.
"""
import json
import logging
from datetime import datetime
from typing import List, Dict

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from sqlmodel import Session, select

from backend.models import UserStyleProfile
from backend.services.agents import get_google_model

logger = logging.getLogger("memory")

# How many messages between consolidation runs
CONSOLIDATION_INTERVAL = 5

# Message counter (per-process; resets on restart — acceptable for a local app)
_message_count = 0


class ExtractedPreferences(BaseModel):
    """Structured output from the memory extractor agent."""
    preferred_colors: list[str] = Field(default_factory=list, description="Colors the user explicitly likes")
    preferred_styles: list[str] = Field(default_factory=list, description="Style keywords the user gravitates toward")
    disliked_elements: list[str] = Field(default_factory=list, description="Things the user said they dislike or want to avoid")
    fit_preferences: str = Field(default="", description="Fit/silhouette preferences mentioned, or empty string")
    custom_notes: str = Field(default="", description="Summary of any other durable style rules or preferences")


memory_extractor_agent = Agent(
    get_google_model(),
    output_type=ExtractedPreferences,
    system_prompt=(
        "You are an expert fashion analyst. Analyze the conversation below between a "
        "personal stylist ('assistant') and their client ('user').\n\n"
        "Extract ONLY durable style preferences, rules, brand affinities, color preferences, "
        "fit preferences, or dislikes that the USER explicitly stated or strongly implied.\n\n"
        "Do NOT extract transient requests (like 'what should I wear today?'). "
        "Focus on lasting preferences that should be remembered for future conversations.\n"
        "If no durable preferences are found, return empty lists and empty strings."
    ),
    retries=1,
)


def should_consolidate() -> bool:
    """Check if it's time to run memory consolidation."""
    global _message_count
    _message_count += 1
    if _message_count >= CONSOLIDATION_INTERVAL:
        _message_count = 0
        return True
    return False


async def consolidate_user_memory(
    recent_messages: List[Dict[str, str]],
    db: Session,
) -> None:
    """
    Background task: distill style preferences from recent chat messages
    and merge them into the UserStyleProfile table.
    """
    if not recent_messages:
        return

    logger.info(f"Running memory consolidation on {len(recent_messages)} recent messages...")

    # Format messages for the extractor agent
    chat_log = "\n".join(
        [f"{msg['role'].upper()}: {msg['content']}" for msg in recent_messages]
    )

    try:
        result = await memory_extractor_agent.run(
            f"[RECENT CONVERSATION]:\n{chat_log}"
        )
        extracted = result.output
        logger.info(f"Extracted preferences: {extracted}")

        # Merge into the database profile (upsert)
        profile = db.exec(select(UserStyleProfile)).first()
        if not profile:
            profile = UserStyleProfile()
            db.add(profile)
            db.commit()
            db.refresh(profile)

        # Merge lists (deduplicate)
        for color in extracted.preferred_colors:
            if color and color not in profile.preferred_colors:
                profile.preferred_colors.append(color)

        for style in extracted.preferred_styles:
            if style and style not in profile.preferred_styles:
                profile.preferred_styles.append(style)

        for dislike in extracted.disliked_elements:
            if dislike and dislike not in profile.disliked_elements:
                profile.disliked_elements.append(dislike)

        # Overwrite scalar fields only if non-empty
        if extracted.fit_preferences:
            profile.fit_preferences = extracted.fit_preferences

        if extracted.custom_notes:
            # Append new notes rather than replacing
            if profile.custom_notes:
                profile.custom_notes = f"{profile.custom_notes}\n{extracted.custom_notes}"
            else:
                profile.custom_notes = extracted.custom_notes

        profile.updated_at = datetime.utcnow()
        db.add(profile)
        db.commit()
        logger.info("Memory consolidation complete — profile updated.")

    except Exception as e:
        logger.error(f"Memory consolidation failed: {e}")
