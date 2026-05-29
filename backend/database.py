import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session, text

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/wardrobe")

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    """Initialize the database: enable pgvector and create all tables."""
    # Ensure the pgvector extension is enabled
    with Session(engine) as session:
        session.exec(text("CREATE EXTENSION IF NOT EXISTS vector"))
        session.commit()
    
    # Create tables defined in models.py
    SQLModel.metadata.create_all(engine)

def get_session():
    """FastAPI session dependency."""
    with Session(engine) as session:
        yield session
