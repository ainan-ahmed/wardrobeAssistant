import os
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import WardrobeItem
from backend.services.vision_pipeline import (
    remove_background,
    extract_metadata,
    generate_embedding,
    ORIGINALS_DIR,
    PROCESSED_DIR
)

logger = logging.getLogger("items_router")
router = APIRouter(prefix="/api/items", tags=["items"])

async def background_ingestion_worker(
    item_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    brand: Optional[str]
):
    """Asynchronous background worker to process image isolation, tagging, and embedding."""
    logger.info(f"Background worker started for item: {item_id}")
    
    # 1. Save original image to disk
    file_ext = os.path.splitext(filename)[1] or ".jpg"
    orig_filename = f"{item_id}_original{file_ext}"
    orig_path = os.path.join(ORIGINALS_DIR, orig_filename)
    
    with open(orig_path, "wb") as f:
        f.write(file_bytes)
        
    # Paths for background removed PNG
    proc_filename = f"{item_id}_processed.png"
    proc_path = os.path.join(PROCESSED_DIR, proc_filename)
    
    # Create a local DB session for the background thread
    from backend.database import engine
    with Session(engine) as session:
        # Fetch the placeholder item
        db_item = session.get(WardrobeItem, item_id)
        if not db_item:
            logger.error(f"Placeholder item {item_id} not found in database.")
            # Clean up raw files if DB item doesn't exist
            if os.path.exists(orig_path):
                os.remove(orig_path)
            return
            
        try:
            # Step 1: Perform cloth-segmented background isolation
            remove_background(orig_path, proc_path)
            
            # Step 2: Trigger Gemini Vision API to parse metadata tags
            metadata = extract_metadata(proc_path)
            
            # Step 3: Generate normalized visual embedding
            embedding = generate_embedding(proc_path)
            
            # Step 4: Update the database record with extracted values
            db_item.original_image_path = orig_path
            db_item.processed_image_path = proc_path
            db_item.category = metadata.get("category", "other")
            db_item.subcategory = metadata.get("subcategory", "unknown")
            db_item.colors = metadata.get("colors", [])
            db_item.style_tags = metadata.get("style_tags", [])
            db_item.ai_description = metadata.get("ai_description", "")
            db_item.vector_embedding = embedding
            
            session.add(db_item)
            session.commit()
            logger.info(f"Background processing completed successfully for item: {item_id}")
            
        except Exception as e:
            logger.error(f"Error processing item {item_id} in background: {str(e)}")
            # Mark database entry as failed
            db_item.category = "failed"
            db_item.ai_description = f"Processing failed: {str(e)}"
            session.add(db_item)
            session.commit()

@router.post("/seed")
async def seed_items(db: Session = Depends(get_session)):
    """Seeds the database with 5 beautifully designed mock items for testing."""
    # Delete existing items
    for item in db.exec(select(WardrobeItem)).all():
        db.delete(item)
    db.commit()

    # Insert mock items
    unit_vector = [0.0] * 512
    unit_vector[0] = 1.0

    items = [
        WardrobeItem(
            id=uuid.uuid4(),
            original_image_path="backend/data/originals/mock_top.jpg",
            processed_image_path="backend/data/processed/mock_top.png",
            category="tops",
            subcategory="sweater",
            colors=["Navy", "White"],
            style_tags=["cozy", "minimalist"],
            ai_description="Premium merino wool navy sweater with white accents",
            brand="Zara",
            times_worn=12,
            is_active=True,
            vector_embedding=unit_vector
        ),
        WardrobeItem(
            id=uuid.uuid4(),
            original_image_path="backend/data/originals/mock_bottom.jpg",
            processed_image_path="backend/data/processed/mock_bottom.png",
            category="bottoms",
            subcategory="jeans",
            colors=["Blue", "Indigo"],
            style_tags=["denim", "classic"],
            ai_description="Classic indigo blue straight-fit jeans",
            brand="Levi's",
            times_worn=8,
            is_active=True,
            vector_embedding=unit_vector
        ),
        WardrobeItem(
            id=uuid.uuid4(),
            original_image_path="backend/data/originals/mock_shoes.jpg",
            processed_image_path="backend/data/processed/mock_shoes.png",
            category="shoes",
            subcategory="sneakers",
            colors=["White", "Grey"],
            style_tags=["athleisure", "sporty"],
            ai_description="Minimalist white leather sneakers with grey stripe",
            brand="Nike",
            times_worn=22,
            is_active=True,
            vector_embedding=unit_vector
        ),
        WardrobeItem(
            id=uuid.uuid4(),
            original_image_path="backend/data/originals/mock_jacket.jpg",
            processed_image_path="backend/data/processed/mock_jacket.png",
            category="outerwear",
            subcategory="jacket",
            colors=["Black"],
            style_tags=["techwear", "waterproof"],
            ai_description="Black lightweight waterproof rain jacket",
            brand="Patagonia",
            times_worn=3,
            is_active=True,
            vector_embedding=unit_vector
        ),
        WardrobeItem(
            id=uuid.uuid4(),
            original_image_path="backend/data/originals/mock_shirt.jpg",
            processed_image_path="backend/data/processed/mock_shirt.png",
            category="tops",
            subcategory="shirt",
            colors=["Pink"],
            style_tags=["formal", "summer"],
            ai_description="Light pink linen summer button-down shirt",
            brand="Ralph Lauren",
            times_worn=1,
            is_active=True,
            vector_embedding=unit_vector
        )
    ]

    for item in items:
        db.add(item)
    db.commit()
    return {"message": "Database seeded successfully!"}

@router.post("/upload", status_code=202)
async def upload_item(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    brand: Optional[str] = Form(None),
    db: Session = Depends(get_session)
):
    """
    Ingests an item:
    1. Instantly creates a placeholder database record with status 'processing'.
    2. Spawns an async background worker to execute heavy segmentation and visual embedding.
    3. Immediately returns 202 Accepted so the UI remains highly interactive.
    """
    item_id = uuid.uuid4()
    logger.info(f"Received upload request. Registering placeholder: {item_id}")
    
    # 1. Read uploaded image bytes
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload file: {str(e)}")
        
    # 2. Persist a placeholder item in the database
    # This allows the frontend to show a loading card in the wardrobe grid instantly
    placeholder_item = WardrobeItem(
        id=item_id,
        original_image_path="",
        processed_image_path="",
        category="processing", # Serves as the loading state flag
        subcategory="processing",
        colors=[],
        style_tags=[],
        ai_description="Isolating apparel and analyzing style tags...",
        brand=brand,
        times_worn=0,
        is_active=True
    )
    db.add(placeholder_item)
    db.commit()
    
    # 3. Hand off heavy processing tasks to the FastAPI background worker pool
    background_tasks.add_task(
        background_ingestion_worker,
        item_id=item_id,
        file_bytes=file_bytes,
        filename=file.filename,
        brand=brand
    )
    
    return {"message": "Upload accepted and queued for background processing", "id": str(item_id)}

@router.get("/", response_model=List[WardrobeItem])
async def list_items(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """Lists wardrobe items with options to filter by category, brand, or run semantic vector searches."""
    # 1. Handle semantic vector search if 'search' query is provided
    if search and search.strip():
        from backend.services.llm_engine import generate_text_embedding
        try:
            query_vector = generate_text_embedding(search)
            statement = (
                select(WardrobeItem)
                .where(WardrobeItem.is_active == True)
                .where(WardrobeItem.category != "processing") # Skip items still in loading state
                .order_by(WardrobeItem.vector_embedding.cosine_distance(query_vector))
            )
            results = db.exec(statement).all()
            return results
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}. Falling back to relational queries.")
            # Fall through to default filters if vector search fails
            
    # 2. Handle standard relational filters
    statement = select(WardrobeItem)
    
    if category:
        statement = statement.where(WardrobeItem.category == category)
    if brand:
        statement = statement.where(WardrobeItem.brand == brand)
        
    # Sort newest items first
    statement = statement.order_by(WardrobeItem.created_at.desc())
    results = db.exec(statement).all()
    return results

@router.get("/{item_id}", response_model=WardrobeItem)
async def get_item(item_id: uuid.UUID, db: Session = Depends(get_session)):
    """Retrieves a single wardrobe item's details."""
    item = db.get(WardrobeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Wardrobe item not found.")
    return item

@router.patch("/{item_id}", response_model=WardrobeItem)
async def update_item(
    item_id: uuid.UUID,
    updated_data: dict,
    db: Session = Depends(get_session)
):
    """Updates selected details (brand, category, is_active, etc.) of an item."""
    db_item = db.get(WardrobeItem, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Wardrobe item not found.")
        
    for key, value in updated_data.items():
        if hasattr(db_item, key):
            setattr(db_item, key, value)
            
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}")
async def delete_item(item_id: uuid.UUID, db: Session = Depends(get_session)):
    """Deletes an item from the database and removes its corresponding image files from disk."""
    db_item = db.get(WardrobeItem, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Wardrobe item not found.")
        
    # Remove files on disk to prevent storage leaks
    if db_item.original_image_path and os.path.exists(db_item.original_image_path):
        try:
            os.remove(db_item.original_image_path)
        except Exception as e:
            logger.warning(f"Failed to delete original file: {db_item.original_image_path}. Error: {str(e)}")
            
    if db_item.processed_image_path and os.path.exists(db_item.processed_image_path):
        try:
            os.remove(db_item.processed_image_path)
        except Exception as e:
            logger.warning(f"Failed to delete processed file: {db_item.processed_image_path}. Error: {str(e)}")
            
    db.delete(db_item)
    db.commit()
    return {"message": "Wardrobe item and associated image files deleted successfully", "id": str(item_id)}
