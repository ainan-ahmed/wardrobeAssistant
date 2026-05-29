import os
import json
import logging
from typing import List, Dict, Any, AsyncGenerator
import open_clip
import torch
import litellm

# DB and Models
from sqlmodel import Session, select
from backend.models import WardrobeItem
from backend.services.vision_pipeline import get_open_clip_model

logger = logging.getLogger("llm_engine")
logging.basicConfig(level=logging.INFO)

# Initialize OpenCLIP text tokenizer for Marqo-FashionSigLIP
_tokenizer = None

def get_tokenizer():
    """Lazy load the OpenCLIP tokenizer."""
    global _tokenizer
    if _tokenizer is None:
        model_name = 'hf-hub:Marqo/marqo-fashionSigLIP'
        logger.info(f"Loading OpenCLIP tokenizer: {model_name}...")
        _tokenizer = open_clip.get_tokenizer(model_name)
    return _tokenizer

def generate_text_embedding(text: str) -> List[float]:
    """Encode search or style queries into a 512-d normalized semantic vector."""
    try:
        # Reuse the loaded model singleton from the vision pipeline
        model, _ = get_open_clip_model()
        tokenizer = get_tokenizer()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Tokenize and encode query text
        text_tokens = tokenizer([text]).to(device)
        
        with torch.no_grad():
            text_features = model.encode_text(text_tokens)
            # Normalize embedding vector
            text_features /= text_features.norm(dim=-1, keepdim=True)
            embedding = text_features[0].cpu().numpy().tolist()
            
        return embedding
    except Exception as e:
        logger.error(f"Error in text embedding generation: {str(e)}")
        raise e

def retrieve_wardrobe_context(user_query: str, db_session: Session, limit: int = 8) -> List[Dict[str, Any]]:
    """Retrieve semantically relevant closet items using pgvector cosine similarity."""
    logger.info(f"Performing pgvector similarity retrieval for query: '{user_query}'")
    try:
        # 1. Convert user text query into a vector
        query_vector = generate_text_embedding(user_query)
        
        # 2. Query PostgreSQL sorted by pgvector's cosine distance operator
        # In SQLModel/SQLAlchemy, pgvector provides the .cosine_distance() helper on vector columns
        statement = (
            select(WardrobeItem)
            .where(WardrobeItem.is_active == True)
            .order_by(WardrobeItem.vector_embedding.cosine_distance(query_vector))
            .limit(limit)
        )
        
        results = db_session.exec(statement).all()
        logger.info(f"Retrieved {len(results)} items from database.")
        
        # 3. Format as simplified metadata for LLM ingestion
        formatted_items = []
        for item in results:
            formatted_items.append({
                "id": str(item.id),
                "category": item.category,
                "subcategory": item.subcategory,
                "brand": item.brand or "Unknown",
                "colors": item.colors,
                "style_tags": item.style_tags,
                "ai_description": item.ai_description or ""
            })
            
        return formatted_items
    except Exception as e:
        logger.error(f"Error retrieving wardrobe context: {str(e)}")
        return []

async def handle_chat_stream(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    db_session: Session
) -> AsyncGenerator[str, None]:
    """
    RAG Styling Stream:
    1. Vectorizes the query and retrieves relevant clothing context.
    2. Builds the lightweight, token-optimized system instruction prompt.
    3. Calls Gemini via litellm with SSE streaming enabled.
    """
    logger.info("Initializing chat stream completion pipeline...")
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        yield "Error: GEMINI_API_KEY is not configured in the environment (.env) file."
        return
        
    try:
        # Step 1: Retrieve relevant wardrobe context
        items_context = retrieve_wardrobe_context(user_message, db_session)
        json_context = json.dumps(items_context, indent=2)
        
        # Step 2: Build the token-optimized system prompt
        system_instruction = (
            "You are \"Aura\", a professional and encouraging personal wardrobe stylist.\n\n"
            "- **Inventory Rule:** Suggest outfits using only the provided closet inventory JSON. Acknowledge alternatives gracefully if requested items are missing.\n"
            "- **UI Render Rule:** Whenever you mention or recommend an item from the closet, you MUST reference it using this exact tag format: `[item:<UUID>]` (e.g. \"Pair your [item:UUID] (Levi's Jeans) with...\"). The UI intercepts this to render interactive clothing cards.\n"
            "- **Style Guidelines:** Keep advice concise. Give a quick \"why\" for your choices (color theory or silhouette balance).\n"
            "- **Format:** Use clear bullet points for outfit breakdowns and bold headers for options.\n\n"
            f"[USER CLOSET INVENTORY FOR THIS QUERY]:\n{json_context}"
        )
        
        # Step 3: Prepare message payload for LiteLLM
        messages = [{"role": "system", "content": system_instruction}]
        
        # Add conversation history (expecting list of {"role": "user"/"assistant", "content": "..."})
        for msg in conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
            
        # Add final user message
        messages.append({"role": "user", "content": user_message})
        
        # Step 4: Stream completions from Gemini via LiteLLM
        logger.info("Requesting streaming completion from gemini-2.5-flash...")
        response = await litellm.acompletion(
            model="gemini/gemini-2.5-flash",
            messages=messages,
            stream=True
        )
        
        # Step 5: Yield text chunks for Server-Sent Events (SSE)
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
                
    except Exception as e:
        logger.error(f"Error in handle_chat_stream: {str(e)}")
        yield f"\n[Stylist Connection Error: {str(e)}]"
