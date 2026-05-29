# **Wardrobe AI Assistant — Complete Development Plan**

## **1\. Project Overview & Core Value**

The goal is to build a single-user personal wardrobe and fashion desktop application.

* **Core Workflow:** Users upload photos of their clothing items.  
* **AI Enrichment:** The application automatically catalogs the uploaded clothing with AI-generated metadata, removes backgrounds, and computes visual embeddings.  
* **Key Features:** Provides outfit suggestions, wardrobe analytics, and a conversational style assistant using Retrieval-Augmented Generation (RAG).

## **2\. Tech Stack Decisions**

This stack merges your initial design with scalable, modern tooling constraints optimized for local development.

* **Development Environment:** Antigravity IDE (used purely as the code editor/environment; no Antigravity SDK is used in the app architecture).  
* **Language:** Python 3.11+  
* **Backend Tooling:** uv (fast Python package and project manager) .  
* **Backend API Framework:** FastAPI.  
* **Database & ORM:** PostgreSQL utilizing the pgvector extension for semantic search, managed via SQLModel.  
* **LLM Orchestration:** litellm (provides a unified, lightweight interface to call standard LLMs).  
* **Vision / Generative LLM:** Google Gemini 2.5 Flash (gemini/gemini-2.5-flash routed via LiteLLM).  
* **Image Background Removal:** rembg (utilizing the u2net\_cloth\_seg model).  
* **Semantic Vectorization:** marqo-fashionSigLIP (loaded via open\_clip). It leverages Generalized Contrastive Learning (GCL) to optimize over seven fashion-specific aspects and significantly outperforms standard CLIP models .  
* **Frontend Framework:** React 18 (scaffolded via Vite).  
* **Frontend Styling:** Mantine v7 (React component library for UI elements like grids, cards, dropzones, and modals) .  
* **Desktop Wrapper:** pywebview (wraps the FastAPI server and Vite build in a native OS window).

## **3\. Project Structure**

The project utilizes uv to manage the backend, ensuring reproducible environments and fast dependency resolution .  
WARDROBE\_AI\_PROJECT/ ├── pyproject.toml \# uv project configuration and dependencies ├── uv.lock \# uv lockfile for exact versioning ├──.env \# Credentials (GEMINI\_API\_KEY, DATABASE\_URL) ├── backend/ │ ├── main.py \# FastAPI entry point & pywebview launcher │ ├── database.py \# PostgreSQL connection & pgvector setup │ ├── models.py \# SQLModel schema definitions │ ├── routers/ \# API routes (items.py, outfits.py, chat.py) │ ├── services/ \# Logic (vision\_pipeline.py, llm\_engine.py) │ └── data/ \# Local storage for images (originals/ & processed/) └── frontend/ ├── package.json \# Vite and Mantine dependencies └── src/ ├── App.jsx \# MantineProvider wrap & Router ├── components/ \# Mantine UI components └── pages/ \# WardrobePage, OutfitsPage, ChatPage

## **4\. Environment & Dependencies Setup**

**Backend (via uv):** Dependencies managed in pyproject.toml using uv add fastapi uvicorn sqlmodel psycopg2-binary pgvector litellm google-generativeai rembg open\_clip\_torch pywebview .  
**Frontend (via npm/yarn):** Dependencies include @mantine/core, @mantine/hooks, @mantine/dropzone, react-router-dom, axios, and zustand .

## **5\. Database Schema (PostgreSQL \+ pgvector)**

PostgreSQL natively supports both relational data and high-dimensional vector embeddings within the same datastore.  
`DEFINE TABLE WardrobeItem (SQLModel):`  
    `FIELD id: UUID (Primary Key)`  
    `FIELD original_image_path: String`  
    `FIELD processed_image_path: String`  
      
    `// AI Metadata (from Gemini via LiteLLM)`  
    `FIELD category: String`   
    `FIELD subcategory: String`  
    `FIELD colors: Array of Strings`  
    `FIELD style_tags: Array of Strings`  
    `FIELD ai_description: String`  
      
    `// Semantic Retrieval Data`  
    `FIELD vector_embedding: Vector (Generated via Marqo-FashionSigLIP)`  
      
    `// User Data & Timestamps`  
    `FIELD brand: String`  
    `FIELD times_worn: Integer`  
    `FIELD is_active: Boolean`  
    `FIELD created_at: Timestamp`

`DEFINE TABLE Outfit (SQLModel):`  
    `FIELD id: UUID`  
    `FIELD name: String`  
    `FIELD item_ids: Array of UUIDs (Foreign Keys to WardrobeItem)`  
    `FIELD occasion: String`  
    `FIELD ai_rationale: String`  
    `FIELD created_at: Timestamp`

`DEFINE TABLE ChatMessage (SQLModel):`  
    `FIELD id: UUID`  
    `FIELD role: String (user/assistant)`  
    `FIELD content: String`  
    `FIELD timestamp: Timestamp`

## **6\. API Route Structure**

* **Items Router (/api/items):**  
  * POST /upload: Uploads an image, processes background removal, runs Gemini vision parsing, and stores the new item.  
  * GET /: Lists items with query parameters (category, season, color, search).  
  * GET /{id}, PATCH /{id}, DELETE /{id}: Standard CRUD operations.  
* **Outfits Router (/api/outfits):**  
  * POST /suggest: Accepts JSON criteria (occasion, weather, style) and returns generated wardrobe recommendations.  
  * GET /, POST /, DELETE /{id}: Outfit history management.  
  * POST /{id}/worn: Increments the worn count for associated items.  
* **Chat Router (/api/chat):**  
  * POST /message: Posts a message to the stylist and returns an SSE stream response.  
  * GET /history, DELETE /history: Chat history management.

## **7\. Service Architectures**

### **Vision & Data Ingestion Pipeline (services/vision\_pipeline.py)**

This service automates the digitization of the user's clothing upon upload.  
`ASYNC FUNCTION process_upload(raw_image_file):`  
    `// 1. Save original image locally`  
    `original_path = RUN save_to_disk(raw_image_file)`  
      
    `// 2. Remove background using rembg`  
    `transparent_image = RUN rembg_with_u2net_cloth_seg(original_path)`  
    `processed_path = RUN save_to_disk(transparent_image)`  
      
    `// 3. Extract Metadata via LiteLLM + Gemini Vision`  
    `messages =}]`  
    `gemini_metadata = RUN litellm.completion(model="gemini/gemini-2.5-flash", messages=messages)`  
      
    `// 4. Generate Semantic Embedding using OpenCLIP`  
    `clothing_vector = RUN open_clip.encode_image('hf-hub:Marqo/marqo-fashionSigLIP', transparent_image)`  
      
    `// 5. Persist to PostgreSQL`  
    `NEW_ITEM = CREATE WardrobeItem(`  
        `image_paths = [original_path, processed_path],`  
        `metadata = PARSE_JSON(gemini_metadata),`  
        `vector_embedding = clothing_vector`  
    `)`  
    `SAVE NEW_ITEM TO PostgreSQL DATABASE`  
      
    `RETURN success_status`

### **AI Recommendation Engine & RAG (services/llm\_engine.py)**

The conversational stylist is powered by LiteLLM, utilizing pgvector to fetch relevant clothing items.  
`FUNCTION retrieve_wardrobe_context(user_query: String):`  
    `// Encode the user's query into a vector`  
    `text_vector = RUN open_clip.encode_text('hf-hub:Marqo/marqo-fashionSigLIP', user_query)`  
      
    `// Query PostgreSQL using pgvector's cosine similarity operator (<=>)`  
    `results = QUERY PostgreSQL:`  
        `SELECT id, category, ai_description, processed_image_path`   
        `FROM WardrobeItem`   
        `ORDER BY vector_embedding <=> text_vector`   
        `LIMIT 10`  
          
    `RETURN FORMAT_AS_TEXT(results)`

`ASYNC FUNCTION handle_chat_stream(user_message, conversation_history):`  
    `// 1. Fetch relevant clothes from the DB based on the query`  
    `wardrobe_context = RUN retrieve_wardrobe_context(user_message)`  
      
    `// 2. Build the system prompt with injected context`  
    `system_instruction = f"You are an expert fashion stylist. Use these wardrobe items: {wardrobe_context}"`  
      
    `// 3. Prepare messages for LiteLLM`  
    `messages = [{"role": "system", "content": system_instruction}]`  
    `messages.EXTEND(conversation_history)`  
    `messages.APPEND({"role": "user", "content": user_message})`  
      
    `// 4. Stream response`  
    `response_stream = RUN litellm.completion(`  
        `model="gemini/gemini-2.5-flash",`   
        `messages=messages,`   
        `stream=True`  
    `)`  
      
    `FOR chunk IN response_stream:`  
        `YIELD chunk`

## **8\. Frontend UI Assembly (React \+ Mantine)**

The React application utilizes Mantine v7 to ensure a clean, responsive interface without writing custom CSS .

* **AppLayout.jsx**: Uses Mantine AppShell to structure the Header, Sidebar navigation, and Main content area .  
* **UploadModal.jsx**: Utilizes the Mantine Dropzone component for drag-and-drop file uploads. It displays a Mantine Loader during processing and triggers a Mantine Notification upon success .  
* **WardrobeGrid.jsx**: Displays items inside a responsive Mantine Grid.  
* **ItemCard.jsx**: Utilizes Mantine Card to display the transparent processed\_image\_path over a neutral background, decorated with Mantine Badge elements for the style tags.  
* **ChatPanel.jsx**: A messaging interface built within a Mantine Paper container, utilizing a Mantine TextInput for sending messages. It natively consumes the SSE stream from the FastAPI backend.  
* **ItemDetailDrawer.jsx**: A right-aligned Mantine Drawer allowing users to edit parsed metadata or log "Worn Today" events.

## **9\. Main Application Launcher (backend/main.py)**

This file orchestrates the local application lifecycle:

1. Connects to PostgreSQL and applies SQLModel table structures.  
2. Launches the FastAPI server via Uvicorn in a background thread running on port 8000\.  
3. Pauses briefly for the server to initialize.  
4. Calls webview.create\_window to open the React app inside a native, resizable desktop window.

## **10\. Development Workflow & Phased Implementation**

* **Phase 1: Foundation & Tooling:** Initialize the project using uv init inside the Antigravity IDE. Scaffold the FastAPI backend and configure the PostgreSQL/pgvector connection. Scaffold the Vite React app and install Mantine core components .  
* **Phase 2: Ingestion Pipeline:** Implement the rembg background removal and configure litellm to call Gemini for JSON metadata extraction. Build the Mantine Dropzone UI and hook it to the /api/items/upload route.  
* **Phase 3: Vectorization & Storage:** Integrate open\_clip to load the marqo-fashionSigLIP model. Generate embeddings for uploaded items and persist them into the PostgreSQL database .  
* **Phase 4: RAG Stylist Engine:** Build the vector similarity search using pgvector's \<=\> operator. Inject the retrieved text context into the litellm streaming pipeline. Build the ChatPanel UI.  
* **Phase 5: Desktop Packaging:** Compile the React frontend to static assets. Wrap the Uvicorn backend and static file delivery inside pywebview for the final native desktop application format.

#### **Works cited**

1\. Best AI Stylists in 2026 – Top 5 free & paid services \- Fits, https://www.fits-app.com/posts/best-ai-stylists-in-2025-top-5-free-paid-services 2\. The Best Wardrobe Apps 2026: Compared & Ranked | Indyx, https://www.myindyx.com/blog/the-best-wardrobe-apps 3\. Capsule Wardrobe Checklist Generator \- Beauty AI, https://beautyai.app/capsule-wardrobe-checklist 4\. patrickjohncyh/fashion-clip \- Hugging Face, https://huggingface.co/patrickjohncyh/fashion-clip
