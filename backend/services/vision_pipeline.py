import os
import uuid
import base64
import json
import logging
from typing import Optional, List, Dict, Any
from PIL import Image

# Third-party libraries
from rembg import remove, new_session
import open_clip
import torch

# DB and Models
from sqlmodel import Session
from backend.models import WardrobeItem

logger = logging.getLogger("vision_pipeline")
logging.basicConfig(level=logging.INFO)

# Directory configurations
DATA_DIR = os.path.join("backend", "data")
ORIGINALS_DIR = os.path.join(DATA_DIR, "originals")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# Ensure storage directories exist
os.makedirs(ORIGINALS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Lazy-loaded model instances for performance
_rembg_session = None
_open_clip_model = None
_open_clip_preprocess = None

def get_rembg_session():
    """Lazy load rembg u2net_cloth_seg session."""
    global _rembg_session
    if _rembg_session is None:
        logger.info("Initializing rembg cloth segmenter model (u2net_cloth_seg)...")
        # u2net_cloth_seg is tailored for clothing background separation
        _rembg_session = new_session("u2net_cloth_seg")
    return _rembg_session

def get_open_clip_model():
    """Lazy load Marqo-FashionSigLIP OpenCLIP model."""
    global _open_clip_model, _open_clip_preprocess
    if _open_clip_model is None:
        model_name = 'hf-hub:Marqo/marqo-fashionSigLIP'
        logger.info(f"Loading OpenCLIP model: {model_name}...")
        
        # Determine execution device (GPU if available, else CPU)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load the model and image preprocessing transforms
        model, _, preprocess = open_clip.create_model_and_transforms(model_name, device=device)
        model = model.to(device)
        model.eval()  # Set model to evaluation mode
        
        _open_clip_model = model
        _open_clip_preprocess = preprocess
        logger.info(f"OpenCLIP model loaded successfully on device: {device}")
        
    return _open_clip_model, _open_clip_preprocess

def remove_background(input_path: str, output_path: str) -> str:
    """Isolate the apparel item and remove the background using rembg."""
    logger.info(f"Removing background from image: {input_path}")
    try:
        input_image = Image.open(input_path)
        session = get_rembg_session()
        
        # Execute background removal
        output_image = remove(input_image, session=session)
        
        # Save as a transparent PNG
        output_image.save(output_path, "PNG")
        logger.info(f"Background removed successfully. Saved to: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error in background removal: {str(e)}")
        raise e

def generate_embedding(image_path: str) -> List[float]:
    """Generate a 512-dimensional fashion-aware semantic embedding for the item."""
    logger.info(f"Generating embedding for image: {image_path}")
    try:
        model, preprocess = get_open_clip_model()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load and preprocess the image
        image = Image.open(image_path).convert("RGB")
        processed_image = preprocess(image).unsqueeze(0).to(device)
        
        # Compute embeddings without gradient calculations
        with torch.no_grad():
            image_features = model.encode_image(processed_image)
            # Normalize embedding vector
            image_features /= image_features.norm(dim=-1, keepdim=True)
            embedding = image_features[0].cpu().numpy().tolist()
            
        logger.info("Embedding generated successfully.")
        return embedding
    except Exception as e:
        logger.error(f"Error in embedding generation: {str(e)}")
        raise e

def encode_image_base64(image_path: str) -> str:
    """Encode an image to a base64 string for API ingestion."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def extract_metadata(image_path: str) -> Dict[str, Any]:
    """Query Gemini via PydanticAI vision agent to parse the apparel item and extract structured metadata."""
    logger.info(f"Extracting AI metadata for image: {image_path}")
    
    # Check if Gemini API key exists
    if not os.getenv("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY is not set in the environment. Returning default metadata.")
        return {
            "category": "unknown",
            "subcategory": "unknown",
            "colors": [],
            "style_tags": [],
            "ai_description": "API Key missing. Metadata could not be extracted."
        }
        
    try:
        from pydantic_ai.messages import BinaryContent
        from backend.services.agents import vision_agent
        
        # Read image bytes for multimodal input
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        prompt = (
            "You are a professional fashion database cataloger. Analyze this clothing image "
            "(which has had its background removed) and extract detailed metadata."
        )
        
        # Call PydanticAI vision agent synchronously (this runs in a background thread)
        result = vision_agent.run_sync(
            [
                prompt,
                BinaryContent(data=image_bytes, media_type="image/png"),
            ]
        )
        
        metadata = result.output
        logger.info(f"Vision agent extracted: {metadata}")
        
        # Convert the Pydantic model to a dict matching the existing pipeline contract
        return metadata.model_dump()
        
    except Exception as e:
        logger.error(f"Error in Gemini metadata extraction: {str(e)}")
        # Return fallback values on API failure
        return {
            "category": "other",
            "subcategory": "unknown",
            "colors": [],
            "style_tags": [],
            "ai_description": f"Failed to catalog item due to API error: {str(e)}"
        }

async def process_upload(
    original_image_bytes: bytes,
    filename: str,
    db_session: Session,
    brand: Optional[str] = None
) -> WardrobeItem:
    """
    Orchestrates the entire ingestion pipeline:
    1. Saves original image to local storage.
    2. Performs cloth-segmented background removal.
    3. Triggers Gemini Vision API to parse metadata.
    4. Computes 512-d visual embeddings using FashionSigLIP.
    5. Saves and returns the fully cataloged WardrobeItem database entry.
    """
    item_id = uuid.uuid4()
    logger.info(f"Initiating ingestion pipeline for new item: {item_id} (Filename: {filename})")
    
    # Save original image
    file_ext = os.path.splitext(filename)[1] or ".jpg"
    orig_filename = f"{item_id}_original{file_ext}"
    orig_path = os.path.join(ORIGINALS_DIR, orig_filename)
    
    with open(orig_path, "wb") as f:
        f.write(original_image_bytes)
        
    # Save processed (transparent bg) image
    proc_filename = f"{item_id}_processed.png"
    proc_path = os.path.join(PROCESSED_DIR, proc_filename)
    
    # Step 1: Remove background
    remove_background(orig_path, proc_path)
    
    # Step 2: Extract visual metadata via Gemini
    metadata = extract_metadata(proc_path)
    
    # Step 3: Compute fashion visual embedding
    embedding = generate_embedding(proc_path)
    
    # Step 4: Write to database
    new_item = WardrobeItem(
        id=item_id,
        original_image_path=orig_path,
        processed_image_path=proc_path,
        category=metadata.get("category", "other"),
        subcategory=metadata.get("subcategory", "unknown"),
        colors=metadata.get("colors", []),
        style_tags=metadata.get("style_tags", []),
        ai_description=metadata.get("ai_description", ""),
        vector_embedding=embedding,
        brand=brand,
        times_worn=0,
        is_active=True
    )
    
    db_session.add(new_item)
    db_session.commit()
    db_session.refresh(new_item)
    
    logger.info(f"Item {item_id} successfully cataloged and persisted to database.")
    return new_item
