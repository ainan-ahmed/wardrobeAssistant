import json
import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import Outfit, WardrobeItem
from backend.services.llm_engine import retrieve_wardrobe_context
from backend.services.agents import outfit_agent, WardrobeDeps

logger = logging.getLogger("outfits_router")
router = APIRouter(prefix="/api/outfits", tags=["outfits"])

@router.post("/suggest", response_model=Outfit)
async def suggest_outfit(
    payload: dict = Body(...),
    db: Session = Depends(get_session)
):
    """
    Accepts criteria (occasion, weather, style) and triggers the PydanticAI outfit
    coordinator agent to select 3-5 matching items from the closet database.
    Returns a guaranteed-structured OutfitRecommendation.
    """
    occasion = payload.get("occasion", "casual")
    weather = payload.get("weather", "mild")
    style = payload.get("style", "minimalist")
    
    logger.info(f"Generating outfit suggestion for Occasion: '{occasion}', Weather: '{weather}', Style: '{style}'")
    
    # 1. Fetch relevant closet items using semantic search
    query_text = f"Clothing items suited for a {occasion} occasion in {weather} weather with a {style} style"
    matching_items = retrieve_wardrobe_context(query_text, db, limit=12)
    
    if not matching_items:
        raise HTTPException(
            status_code=400,
            detail="Your wardrobe is empty! Please upload clothing items first before requesting recommendations."
        )
        
    # 2. Query the PydanticAI outfit agent for a structured recommendation
    try:
        prompt = (
            "You are a professional fashion editor. Co-ordinate one stylish, cohesive outfit by selecting "
            "between 2 to 5 items from the provided list of closet items. Do not invent any items.\n\n"
            "Here is the list of available closet items:\n"
            f"{json.dumps(matching_items, indent=2)}\n\n"
            f"Occasion: {occasion}\nWeather: {weather}\nVibe: {style}\n"
        )
        
        result = await outfit_agent.run(prompt, deps=WardrobeDeps(db=db))
        recommendation = result.output
        
        # 3. Save and return the Outfit record
        new_outfit = Outfit(
            id=uuid.uuid4(),
            name=recommendation.name,
            item_ids=[str(i) for i in recommendation.item_ids],
            occasion=occasion,
            ai_rationale=recommendation.ai_rationale,
        )
        
        db.add(new_outfit)
        db.commit()
        db.refresh(new_outfit)
        
        return new_outfit
        
    except Exception as e:
        logger.error(f"Failed to generate outfit recommendation: {e}")
        # Provide a simple local heuristic fallback if agent or API fails
        selected_ids = [item["id"] for item in matching_items[:2]]
        new_outfit = Outfit(
            id=uuid.uuid4(),
            name=f"Standard Outfit ({occasion})",
            item_ids=selected_ids,
            occasion=occasion,
            ai_rationale=f"Failed to call AI: {e}. Compiled simple fallback look with top inventory matches.",
        )
        db.add(new_outfit)
        db.commit()
        db.refresh(new_outfit)
        return new_outfit

@router.get("/", response_model=List[Outfit])
async def list_outfits(db: Session = Depends(get_session)):
    """Lists outfit recommendation history sorted by newest first."""
    statement = select(Outfit).order_by(Outfit.created_at.desc())
    results = db.exec(statement).all()
    return results

@router.post("/{outfit_id}/worn")
async def log_outfit_worn(outfit_id: uuid.UUID, db: Session = Depends(get_session)):
    """Increments the times_worn field by 1 for all items associated with this outfit."""
    outfit = db.get(Outfit, outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found.")
        
    updated_items = []
    for item_id_str in outfit.item_ids:
        try:
            item_uuid = uuid.UUID(item_id_str)
            item = db.get(WardrobeItem, item_uuid)
            if item:
                item.times_worn += 1
                db.add(item)
                updated_items.append(str(item.id))
        except Exception as e:
            logger.warning(f"Invalid UUID '{item_id_str}' stored in Outfit {outfit_id}: {e}")
            
    db.commit()
    return {"message": "Outfit wear registered successfully.", "worn_items": updated_items}

@router.delete("/{outfit_id}")
async def delete_outfit(outfit_id: uuid.UUID, db: Session = Depends(get_session)):
    """Deletes an outfit recommendation from history."""
    outfit = db.get(Outfit, outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found.")
        
    db.delete(outfit)
    db.commit()
    return {"message": "Outfit deleted successfully", "id": str(outfit_id)}
