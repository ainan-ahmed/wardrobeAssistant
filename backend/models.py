import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.postgresql import JSON
from pgvector.sqlalchemy import Vector

class WardrobeItem(SQLModel, table=True):
    __tablename__ = "wardrobe_item"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    original_image_path: str = Field(nullable=False)
    processed_image_path: str = Field(nullable=False)
    
    # AI Metadata (extracted via Gemini)
    category: str = Field(index=True, nullable=False)  # e.g., tops, bottoms, shoes, outerwear
    subcategory: Optional[str] = Field(default=None)   # e.g., t-shirt, jeans, jacket
    colors: List[str] = Field(default=[], sa_column=Column(JSON))
    style_tags: List[str] = Field(default=[], sa_column=Column(JSON))
    ai_description: Optional[str] = Field(default=None)

    # Semantic Retrieval Data (FashionSigLIP is 512 dimensions)
    # Using sa_column with pgvector's Vector type
    vector_embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(512), nullable=True)
    )

    # User Data & Timestamps
    brand: Optional[str] = Field(default=None, index=True)
    times_worn: int = Field(default=0)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

class Outfit(SQLModel, table=True):
    __tablename__ = "outfit"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    name: str = Field(nullable=False)
    item_ids: List[str] = Field(default=[], sa_column=Column(JSON)) # List of WardrobeItem UUIDs
    occasion: Optional[str] = Field(default=None, index=True)
    ai_rationale: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_message"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    role: str = Field(nullable=False) # "user" or "assistant"
    content: str = Field(nullable=False)
    timestamp: datetime = Field(default_factory=datetime.utcnow, nullable=False)
