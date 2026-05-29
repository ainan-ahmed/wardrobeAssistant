import os
import sys
import asyncio
from PIL import Image, ImageDraw

# Add current workspace to path to allow backend imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from sqlmodel import Session
from backend.database import init_db, engine
from backend.services.vision_pipeline import process_upload

def create_dummy_image(path: str):
    """Create a basic clothing-shaped image for local validation."""
    print(f"Creating a sample mock clothing image at: {path}")
    # Create a 300x300 canvas with a transparent background
    img = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a simple green shirt shape
    # Torso
    draw.rectangle([100, 100, 200, 250], fill=(46, 204, 113, 255))
    # Left Sleeve
    draw.polygon([(100, 100), (70, 140), (90, 150), (100, 120)], fill=(46, 204, 113, 255))
    # Right Sleeve
    draw.polygon([(200, 100), (230, 140), (210, 150), (200, 120)], fill=(46, 204, 113, 255))
    
    img.save(path, "PNG")

async def test_pipeline():
    print("=" * 60)
    print("WARDROBE AI ASSISTANT — INGESTION PIPELINE VERIFICATION")
    print("=" * 60)
    
    # Initialize DB (creates schema & extensions)
    print("\n[Step 1] Initializing local database schema...")
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {str(e)}")
        print("Note: Ensure your Docker database container is running (docker compose up -d)")
        return

    # Create dummy image to feed into the pipeline
    dummy_path = "mock_tshirt.png"
    create_dummy_image(dummy_path)
    
    try:
        # Read the mock image bytes
        with open(dummy_path, "rb") as f:
            image_bytes = f.read()

        print("\n[Step 2] Processing mock image through vision ingestion pipeline...")
        print("(This will isolate the clothes, call Gemini for tags, and generate a 512-d OpenCLIP embedding)")
        
        with Session(engine) as session:
            # Trigger full ingestion
            item = await process_upload(
                original_image_bytes=image_bytes,
                filename="mock_tshirt.png",
                db_session=session,
                brand="AI Mock Brand"
            )
            
            print("\n" + "=" * 40)
            print("PIPELINE PROCESSING SUCCESSFUL!")
            print("=" * 40)
            print(f"Item ID:               {item.id}")
            print(f"Original Image Path:   {item.original_image_path}")
            print(f"Processed Image Path:  {item.processed_image_path}")
            print(f"Parsed Category:       {item.category}")
            print(f"Parsed Subcategory:    {item.subcategory}")
            print(f"Extracted Colors:      {item.colors}")
            print(f"Style Tags:            {item.style_tags}")
            print(f"AI Description:        {item.ai_description}")
            if item.vector_embedding:
                print(f"Vector dimensions:     {len(item.vector_embedding)}")
                print(f"First 5 vector values: {item.vector_embedding[:5]}")
            else:
                print("Vector Embedding:      Not generated (None)")
            print("=" * 40)

    except Exception as e:
        print(f"\n[ERROR] Pipeline test failed: {str(e)}")
    finally:
        # Clean up temporary test file
        if os.path.exists(dummy_path):
            os.remove(dummy_path)
            print("\nCleaned up mock t-shirt file.")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
