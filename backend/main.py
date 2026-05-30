import os
import sys
import time
import threading
import logging
import argparse

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import DB and Routers
from backend.database import init_db
from backend.routers import items, chat, outfits

logger = logging.getLogger("main_launcher")
logging.basicConfig(level=logging.INFO)

# --- FASTAPI SERVER DEFINITION ---
app = FastAPI(title="wardrobeAssistant Backend", version="0.1.0")

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount DB data directories as static folders to serve isolated cutout images
# This allows the React app to render pictures directly from /backend/data/...
data_directory = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_directory, exist_ok=True)
app.mount("/backend/data", StaticFiles(directory=data_directory), name="data")

# Mount API routers
app.include_router(items.router)
app.include_router(chat.router)
app.include_router(outfits.router)

# Mount frontend production build static files if present
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    logger.warning("Production frontend build directory 'frontend/dist' not found. Ensure frontend is built or dev server is running.")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "wardrobe-assistant-backend"}

# --- DOUBLE-THREADING ORCHESTRATION ---

class BackgroundServer(threading.Thread):
    """Custom thread to manage Uvicorn lifecycle alongside pywebview."""
    def __init__(self):
        super().__init__()
        self.config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
        self.server = uvicorn.Server(self.config)

    def run(self):
        logger.info("Starting background Uvicorn server on port 8000...")
        self.server.run()

    def stop(self):
        logger.info("Stopping background Uvicorn server...")
        self.server.should_exit = True

def is_port_open(host: str, port: int) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False

def start_desktop_app():
    # Lazy-load webview to prevent native GUI library initialization/imports in headless server mode
    import webview

    # 1. Initialize PostgreSQL schema and pgvector
    logger.info("Initializing local PostgreSQL schema and vector extension...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        logger.error("Please ensure your local Docker pgvector database is running (docker compose up -d)")
        # In a development fallback, we continue to allow window opening
        
    # 2. Boot FastAPI Uvicorn ASGI server in a dedicated background worker thread
    server_thread = BackgroundServer()
    server_thread.daemon = True
    server_thread.start()
    
    # Pause briefly for the backend thread to start listening
    time.sleep(1.0)
    
    # 3. Create a native resizable desktop window pointing to the local Vite dev server
    # (or fallback to compiled static files served via FastAPI)
    if is_port_open("127.0.0.1", 5173):
        dev_url = "http://127.0.0.1:5173"
        logger.info(f"Vite dev server detected. Launching pywebview pointing to dev: {dev_url}")
    else:
        dev_url = "http://127.0.0.1:8000"
        logger.info(f"Vite dev server not found on port 5173. Launching pywebview pointing to FastAPI production server: {dev_url}")
    
    window = webview.create_window(
        title="👗 wardrobeAssistant",
        url=dev_url,
        width=1100,
        height=750,
        resizable=True,
        min_size=(900, 600)
    )
    
    # 4. Block on pywebview execution (this blocks the main execution thread)
    # When the GUI window is closed, this function returns, letting us run cleanups
    webview.start()
    
    # 5. Clean termination of Uvicorn server thread
    server_thread.stop()
    logger.info("Application shut down cleanly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="wardrobeAssistant App Launcher")
    parser.add_argument(
        "--server", 
        action="store_true", 
        help="Start the FastAPI backend server only (bypassing the native pywebview desktop GUI)"
    )
    args = parser.parse_args()

    if args.server:
        logger.info("Starting in Pure Server Mode (No GUI)...")
        # 1. Initialize PostgreSQL schema and pgvector
        logger.info("Initializing local PostgreSQL schema and vector extension...")
        try:
            init_db()
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            logger.error("Please ensure your local Docker pgvector database is running (docker compose up -d)")
        
        # 2. Start Uvicorn directly on the main thread with standard logging info level
        logger.info("Starting FastAPI Uvicorn server on http://127.0.0.1:8000 (main thread)...")
        try:
            uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
        except KeyboardInterrupt:
            logger.info("Uvicorn server stopped by user (KeyboardInterrupt).")
    else:
        start_desktop_app()
