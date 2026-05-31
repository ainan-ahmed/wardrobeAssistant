"""
LLM Engine — CLIP-specific vector search utilities.

This module handles text-to-vector encoding using the local Marqo-FashionSigLIP
model for semantic wardrobe searches. Chat completion logic has been moved to
backend/services/agents.py (PydanticAI).
"""
import logging
from typing import List, Dict, Any
import open_clip
import torch

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
        try:
            statement = (
                select(WardrobeItem)
                .where(WardrobeItem.is_active == True)
                .order_by(WardrobeItem.vector_embedding.cosine_distance(query_vector))
                .limit(limit)
            )
            results = db_session.exec(statement).all()
        except Exception as vec_err:
            logger.warning(f"Vector search failed: {vec_err}. Falling back to relational newest first.")
            statement = (
                select(WardrobeItem)
                .where(WardrobeItem.is_active == True)
                .order_by(WardrobeItem.created_at.desc())
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
