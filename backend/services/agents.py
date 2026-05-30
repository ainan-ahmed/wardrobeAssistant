"""
Central PydanticAI agent definitions for the Wardrobe Assistant.

All agents share the same GoogleModel instance pointing to gemini-2.5-flash,
and use WardrobeDeps for dependency injection of the database session.
"""
import os
import json
import logging
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from sqlmodel import Session, select

from backend.models import WardrobeItem, UserStyleProfile

logger = logging.getLogger("agents")

# ── Shared Model & Dependencies ──────────────────────────────────────────────

def get_google_model() -> GoogleModel:
    """Create the GoogleModel instance. Uses GEMINI_API_KEY from environment."""
    provider = GoogleProvider(api_key=os.getenv("GEMINI_API_KEY"))
    return GoogleModel(
        "gemini-2.5-flash",
        provider=provider,
    )


@dataclass
class WardrobeDeps:
    """Shared dependency context injected into all PydanticAI agents at runtime."""
    db: Session


# ── Helper: Retrieve wardrobe text context ───────────────────────────────────

def _retrieve_wardrobe_text(db: Session) -> str:
    """Fetch active wardrobe items as a compact JSON context string."""
    statement = select(WardrobeItem).where(WardrobeItem.is_active == True)
    results = db.exec(statement).all()
    items = []
    for item in results:
        items.append({
            "id": str(item.id),
            "category": item.category,
            "subcategory": item.subcategory,
            "brand": item.brand or "Unknown",
            "colors": item.colors,
            "style_tags": item.style_tags,
            "ai_description": item.ai_description or "",
        })
    return json.dumps(items, indent=2)


def _retrieve_style_profile(db: Session) -> Optional[UserStyleProfile]:
    """Fetch the single user style profile (first row)."""
    statement = select(UserStyleProfile)
    return db.exec(statement).first()


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 1: Stylist Chat Agent
# ═══════════════════════════════════════════════════════════════════════════════

stylist_agent = Agent(
    get_google_model(),
    deps_type=WardrobeDeps,
    output_type=str,
    retries=2,
)


@stylist_agent.system_prompt
async def build_stylist_context(ctx: RunContext[WardrobeDeps]) -> str:
    """Dynamically builds the system prompt by querying the DB for wardrobe items and style profile."""
    wardrobe_json = _retrieve_wardrobe_text(ctx.deps.db)
    profile = _retrieve_style_profile(ctx.deps.db)

    profile_section = ""
    if profile:
        profile_section = (
            "\n[USER'S STYLE PROFILE & DNA]:\n"
            f"- Preferred Colors: {profile.preferred_colors}\n"
            f"- Preferred Styles: {profile.preferred_styles}\n"
            f"- Disliked Elements/Rules: {profile.disliked_elements}\n"
            f"- Fit Preferences: {profile.fit_preferences or 'No preference stated'}\n"
            f"- Styling Notes: {profile.custom_notes or 'None yet'}\n"
        )

    return (
        'You are "Aura", a professional and encouraging personal wardrobe stylist.\n\n'
        "- **Inventory Rule:** Suggest outfits using only the provided closet inventory JSON. "
        "Acknowledge alternatives gracefully if requested items are missing.\n"
        "- **UI Render Rule:** Whenever you mention or recommend an item from the closet, "
        'you MUST reference it using this exact tag format: `[item:<UUID>]` '
        '(e.g. "Pair your [item:UUID] (Levi\'s Jeans) with...").\n'
        "- **Style Guidelines:** Keep advice concise. Give a quick \"why\" for your choices "
        "(color theory or silhouette balance).\n"
        "- **Format:** Use clear bullet points for outfit breakdowns and bold headers for options.\n"
        f"{profile_section}\n"
        f"[USER CLOSET INVENTORY FOR THIS QUERY]:\n{wardrobe_json}"
    )


@stylist_agent.tool
async def update_style_preference(
    ctx: RunContext[WardrobeDeps],
    preference_type: str,
    value: str,
) -> str:
    """Save a style preference the user explicitly stated during conversation.

    Args:
        preference_type: One of 'color', 'style', 'dislike', 'fit'.
        value: The preference value to store (e.g. 'navy blue', 'oversized tops').
    """
    db = ctx.deps.db
    profile = _retrieve_style_profile(db)
    if not profile:
        profile = UserStyleProfile()
        db.add(profile)
        db.commit()
        db.refresh(profile)

    if preference_type == "color" and value not in profile.preferred_colors:
        profile.preferred_colors.append(value)
    elif preference_type == "style" and value not in profile.preferred_styles:
        profile.preferred_styles.append(value)
    elif preference_type == "dislike" and value not in profile.disliked_elements:
        profile.disliked_elements.append(value)
    elif preference_type == "fit":
        profile.fit_preferences = value

    db.add(profile)
    db.commit()
    return f"Noted! Saved {preference_type} preference: {value}."


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 2: Outfit Coordinator Agent (Structured Output)
# ═══════════════════════════════════════════════════════════════════════════════

class OutfitRecommendation(BaseModel):
    """Guaranteed structured output from the outfit coordinator agent."""
    name: str = Field(description="A creative, stylish name for this outfit combination")
    item_ids: list[str] = Field(description="UUIDs of the selected closet items")
    ai_rationale: str = Field(description="Two-sentence styling rationale explaining the coordination")


outfit_agent = Agent(
    get_google_model(),
    output_type=OutfitRecommendation,
    deps_type=WardrobeDeps,
    retries=2,
)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 3: Vision Metadata Agent (Structured Output)
# ═══════════════════════════════════════════════════════════════════════════════

class ClothingMetadata(BaseModel):
    """Guaranteed structured output from the vision metadata extraction agent."""
    category: str = Field(description="One of: tops, bottoms, shoes, outerwear, accessories, other")
    subcategory: str = Field(description="e.g. t-shirt, sweater, jeans, shorts, sneakers, boots, jacket")
    colors: list[str] = Field(description="List of principal colors, e.g. Black, Navy Blue, Crimson")
    style_tags: list[str] = Field(description="3-5 style descriptors, e.g. streetwear, minimalist, casual")
    ai_description: str = Field(description="Concise one-sentence description of the item's appearance")


vision_agent = Agent(
    get_google_model(),
    output_type=ClothingMetadata,
    retries=2,
)
