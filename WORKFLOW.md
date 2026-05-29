# wardrobeAssistant Workflow

This file describes the backend execution flow, lazy loading patterns, and where each AI processing component fits in the lifecycle.

---

## 1) Process Startup

1. **Docker Setup:** Run `docker compose up -d` to launch the PostgreSQL database container with the `pgvector` extension enabled on port `5433`.
2. **App Launcher:** Execute `uv run backend/main.py` to start the application.
3. **Double-Threading Orchestrator:** `backend/main.py` boots:
   - **Database Connection Engine:** Connects to PostgreSQL, runs an SQL script ensuring the `vector` extension is enabled, and applies SQLModel metadata tables auto-creation.
   - **ASGI FastAPI Daemon:** Launches a Uvicorn server in a dedicated background thread running on port `8000`.
   - **Desktop Shell Window:** Main thread creates a native desktop window pointing to the compiled static frontend files using `pywebview`.

---

## 2) Lazy Runtime Initialization

AI models are heavy and consume significant system resources. To keep application startup instant, models are lazy-loaded as singletons on their first request rather than during program boot:

* **Background Isolation Session (`rembg`):** Loaded only when an upload is first triggered. Initializes the `u2net_cloth_seg` segmenter session.
* **OpenCLIP Model (`open_clip`):** Loaded only when the first image upload or search query is made. Initializes `Marqo/marqo-fashionSigLIP` and places weights on GPU (if CUDA-enabled) or CPU.

Once loaded, both instances reside in memory as global singletons for sub-second execution on subsequent uploads and queries.

---

## 3) Async Image Ingestion Flow (`/api/items/upload` -> Background Task)

1. **Image Drop:** User uploads a clothing image via the Mantine Dropzone.
2. **Immediate Ingestion Feedback:** The `/api/items/upload` route:
   - Generates a unique UUID for the new item.
   - Instantly creates a placeholder `WardrobeItem` database record with `category="processing"` and `subcategory="processing"` (representing the loading state).
   - Queues the heavy AI processing pipeline into a FastAPI `BackgroundTask`.
   - Immediately returns a `202 Accepted` response containing the item UUID so the user interface can display a loading card with a spinner in the wardrobe grid instantly.
3. **Sequential Background Worker:** The background task (`background_ingestion_worker`) executes:
   - **File Storage:** Saves the raw uploaded file bytes under `backend/data/originals/` as `<UUID>_original.<ext>`.
   - **Background Isolation:** Passes the original image to `remove_background()` which isolates the apparel cutout and saves a transparent PNG under `backend/data/processed/` as `<UUID>_processed.png`.
   - **Gemini Multimodal Categorizer:** Passes the base64-encoded transparent PNG to `gemini-2.5-flash` via `litellm` requesting a structured JSON object containing categories, subcategories, colors, style tags, and descriptions.
   - **Fashion Embedding Generation:** Passes the transparent PNG to the local `Marqo-FashionSigLIP` OpenCLIP model to generate a normalized 512-dimensional visual vector embedding.
   - **Database Update:** Updates the pre-existing placeholder database record with the actual extracted metadata and vector embedding, transitionally updating the item's state in the UI. On processing errors, it sets `category="failed"` to notify the user.

---

## 4) Lookalike Retrieval & similarity Search

To match items against user text prompts (e.g. *"Find a blue jacket similar to my vintage coat"*):

1. **Text Query Vectorization:** The query text is encoded using the OpenCLIP `Marqo-FashionSigLIP` text encoder, producing a 512-dimensional search vector.
2. **PostgreSQL Similarity query:** The backend issues a SQLModel query using pgvector's native cosine distance operator (`<=>`):
   ```sql
   SELECT id, category, ai_description, processed_image_path
   FROM wardrobe_item
   ORDER BY vector_embedding <=> :text_vector
   LIMIT 10
   ```
3. **Results:** The database performs an ultra-fast, high-dimensional similarity comparison and returns the top matching clothes items.

---

## 5) Conversational Stylist & RAG Stream

The stylist assistant uses Retrieval-Augmented Generation (RAG) to provide contextual, personalized fashion advice:

1. **Context Extraction:** User's message is vectorized, and relevant wardrobe items are fetched using similarity searches.
2. **Prompt Injection:** A system prompt is built dynamically, injecting the user's specific closet item details (category, brand, style tags, description) as context:
   ```
   You are an expert fashion stylist. Use these wardrobe items: [Injected Wardrobe Context]
   ```
3. **LiteLLM Streaming Completion:** The message history and custom system prompt are sent to `gemini-2.5-flash`.
4. **SSE Event Stream:** LiteLLM returns a real-time generator, which the `/api/chat/message` router streams back to the React `ChatPanel` client using **Server-Sent Events (SSE)**.
