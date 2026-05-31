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
   - **Structured Metadata Extraction (PydanticAI Vision Agent):** Passes the transparent PNG's raw bytes to the PydanticAI `vision_agent` running `gemini-2.5-flash`. The agent uses the guaranteed `ClothingMetadata` schema to return structured fields: `category`, `subcategory`, `colors`, `style_tags`, and `ai_description`.
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

## 5) Stateful Conversational Stylist ("Aura") & SSE Stream

The stylist assistant uses PydanticAI's `stylist_agent` to provide contextual, highly personalized fashion advice:

1. **Dynamic Prompt Context Building:** At runtime, the agent's `@stylist_agent.system_prompt` decorator executes a query to:
   - Retrieve all active wardrobe items as a compact, structured JSON text block (`_retrieve_wardrobe_text`). This decouples chat from OpenCLIP embeddings, saving local memory and CPU.
   - Retrieve the user's persistent preference profile (`UserStyleProfile`) including preferred/disliked colors, styles, fit rules, and styling notes.
2. **System Prompt Composition:** The agent injects this metadata into a set of personality guidelines ("Aura" personal stylist), strict UI item-referencing rules (matching items using `[item:<UUID>]` tags for frontend hydration), and style guidelines.
3. **PydanticAI Tool Call (`update_style_preference`):** If the user explicitly mentions a style choice during the conversation (e.g., *"I love oversized fits"* or *"I hate neon green"*), the agent invokes its tool automatically to persist the rule inside `UserStyleProfile`.
4. **SSE Event Stream (`/api/chat/stream`):** PydanticAI streaming runs `stylist_agent.run_stream(..., deps=WardrobeDeps(db=db))` in an asynchronous event generator. The router streams text delta chunks as standard Server-Sent Events (SSE) back to the frontend.
5. **Memory & Consolidation:** On stream completion, the full assistant reply is saved to the chat history database, and an asynchronous background task checks if user memory needs to be consolidated.

---

## 6) Outfit Coordinator Agent (`/api/outfits/suggest`)

To coordinate a stylish, cohesive outfit from the user's actual closet:

1. **Auto-Weather Geolocation Context (Optional):**
   * If `Use Auto-Weather (Local)` is toggled ON, the React frontend requests browser geolocation (`navigator.geolocation.getCurrentPosition`).
   * It dynamically queries the Open-Meteo API using the coordinates: `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true`.
   * Maps WMO weather codes to a text description and appends current temperature (e.g. `"Overcast, 22.1°C"`).
   * Locks the weather input field in the UI, and passes this live environmental string in the `/api/outfits/suggest` request payload.
2. **Robust Semantic Context Retrieval (with Fallback):**
   * Based on occasion, weather, and vibe parameters, the system encodes the criteria text using the local OpenCLIP tokenizer (`retrieve_wardrobe_context`) to construct a search query vector.
   * **Fault-Tolerant pgvector Query:** The backend attempts a SQLModel similarity query sorted by pgvector's cosine distance operator against `vector_embedding` columns.
   * **Relational Fallback:** If pgvector calculations fail (e.g., if visual embeddings are not yet populated/cached by background workers or mock seeding data is loaded), the search catches the database exception and **automatically falls back to a relational newest-first query**. This ensures outfit suggestions never throw a 400 Bad Request error even in dry database states.
3. **PydanticAI Outfit Agent Orchestration:** The backend supplies these matching items as context to the `outfit_agent`, which is configured with a structured output type `OutfitRecommendation`.
4. **Guaranteed Structured Output:** The LLM output is validated against the `OutfitRecommendation` schema:
   - `name`: A creative, stylish name for the combination.
   - `item_ids`: A verified list of closet UUIDs selected from the input (no invented items).
   - `ai_rationale`: A two-sentence fashion rationale explaining the match.
5. **Database Persistence:** The validated recommendation is stored as an `Outfit` database record and served to the user interface.

---

## 7) Wardrobe Analytics Insights (`AnalyticsTab.tsx`)

To provide rich, real-time insights without introducing heavy backend load, the application computes high-fidelity analytics on the client-side using existing wardrobe inventory data:

1. **closet Inventory Retrieval:** The dashboard retrieves the full list of active wardrobe items polled from `/api/items/` (which auto-refreshes every 3.5 seconds).
2. **Color Palette Percentage breakdown:**
   * Gathers all color arrays from active items and calculates the global occurrence frequency of each unique color.
   * Computes the percentage distribution and renders a beautiful multi-segmented Mantine `<Progress>` bar.
   * Uses tailored color shades to map custom colors (`Navy`, `Amber`, `Cream`, etc.) and renders corresponding active badges.
3. **Hero Items (Most Worn):**
   * Sorts the closet items in descending order of their `times_worn` field.
   * Renders the top 5 most frequently worn garments, marked with a prominent green badge to represent your core "Closet Heroes".
4. **Dead Weight (Least Worn):**
   * Filters active items and sorts them in ascending order of their `times_worn` field.
   * Renders the bottom 5 least frequently worn items, marked with a prominent red warning badge to identify apparel that is underutilized or ready for donation/re-styling.

