# wardrobeAssistant Agent Notes

## Reality checks first

- **Docker Database dependency:** Standard database operations require the local Docker container to be running. If the database connection fails, make sure you start the container (`docker compose up -d`).
- **Dependencies footprint:** LiteLLM and OpenCLIP load numerous sub-dependencies (PyTorch, Tokenizers, HuggingFace clients). Let `uv` finish syncing them cleanly.
- **Syntactic sanity checks:** No standard CI, pre-commit, or mypy configs exist in the project. Run Python compilation checks before making major edits.
- **State Ground Truth:** Trust the schema declarations in `backend/models.py` and the routes in `backend/routers/` for actual API interface shapes.

## Commands that actually work

- **Sync backend virtual environment:**
  ```bash
  uv sync
  ```
- **Activate virtual environment:**
  ```bash
  source .venv/bin/activate
  ```
- **Start the PostgreSQL pgvector container:**
  ```bash
  docker compose up -d
  ```
- **Shut down the database container:**
  ```bash
  docker compose down
  ```
- **Run the pipeline sanity checker:**
  ```bash
  uv run verify_pipeline.py
  ```
- **Fast sanity compile check:**
  ```bash
  uv run python -m py_compile backend/database.py backend/models.py backend/services/vision_pipeline.py backend/services/llm_engine.py backend/routers/items.py backend/routers/chat.py backend/routers/outfits.py
  ```
- **Inspect the running container schema directly:**
  ```bash
  docker exec -it wardrobe_db psql -U postgres -d wardrobe -c "\dt"
  ```

## Core execution flow

- **Database Initializer:** `backend/database.py::init_db()` executes raw SQL to guarantee `CREATE EXTENSION IF NOT EXISTS vector` runs BEFORE trying to register tables, avoiding PGVector relational schema errors.
- **Model Lazy Singletons:** Global ML models (`rembg` clothing segmenter and `open_clip` OpenCLIP embeddings) are lazy-loaded singletons in `backend/services/vision_pipeline.py` and `backend/services/llm_engine.py` to prevent heavy lag during window startup. They load on the first request and persist in memory.
- **Non-Blocking Ingestion Pipeline:** `/api/items/upload` creates a database record with a `category="processing"` placeholder immediately, hands off heavy visual processing tasks (background erasure, Gemini tagging, OpenCLIP vectorization) to a FastAPI `BackgroundTask`, and returns `202 Accepted` instantly.
- **pgvector Cosine Similarity:** Semantic lookalike query searches are done using pgvector-sqlalchemy's native column function `WardrobeItem.vector_embedding.cosine_distance(query_vector)`, translating directly to the SQL `<=>` operator.
- **Aura Stylist Prompt Injection:** The conversational RAG system vectorizes the message, extracts similar closet matches, encodes them in a compact JSON context block, prepends the condensed, token-saving prompt instructions, and streams SSE chunks using LiteLLM and `gemini-2.5-flash`.
