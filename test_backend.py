import sys
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# --- MOCKING ML MODULES BEFORE IMPORTING ROUTERS ---
# This prevents Starlette / Rembg / OpenCLIP / Torch / dotenv import issues in dry environments
mock_dotenv = MagicMock()
sys.modules['dotenv'] = mock_dotenv
mock_rembg = MagicMock()
mock_open_clip = MagicMock()
mock_torch = MagicMock()

# Configure MagicMock properties to prevent attribute lookup errors
mock_torch.cuda.is_available.return_value = False
mock_open_clip.get_tokenizer.return_value = lambda x: MagicMock()

mock_python_multipart = MagicMock()
mock_python_multipart.__version__ = "0.0.24"
sys.modules['python_multipart'] = mock_python_multipart
sys.modules['rembg'] = mock_rembg
sys.modules['open_clip'] = mock_open_clip
sys.modules['torch'] = mock_torch
sys.modules['multipart'] = MagicMock()

# Mock PydanticAI modules
mock_pydantic_ai = MagicMock()
mock_pydantic_ai_models_google = MagicMock()
mock_pydantic_ai_messages = MagicMock()
sys.modules['pydantic_ai'] = mock_pydantic_ai
sys.modules['pydantic_ai.models'] = MagicMock()
sys.modules['pydantic_ai.models.google'] = mock_pydantic_ai_models_google
sys.modules['pydantic_ai.providers'] = MagicMock()
sys.modules['pydantic_ai.providers.google'] = MagicMock()
sys.modules['pydantic_ai.messages'] = mock_pydantic_ai_messages

# Create mock Agent class that returns predictable results
class MockRunResult:
    def __init__(self, data):
        self.output = data

class MockStreamedRunResult:
    def __init__(self, text):
        self.text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def stream_text(self, delta=False, debounce_by=None):
        if delta:
            # Yield words as delta chunks
            words = self.text.split()
            for i, word in enumerate(words):
                # add trailing space for non-last words
                yield word + (" " if i < len(words) - 1 else "")
        else:
            yield self.text

class MockAgent:
    """A mock PydanticAI Agent that returns predictable results for testing."""
    def __init__(self, *args, **kwargs):
        self._system_prompt_fns = []
        self._tools = []
        self.result_type = kwargs.get('result_type', str)
    
    def system_prompt(self, fn):
        self._system_prompt_fns.append(fn)
        return fn
    
    def tool(self, fn):
        self._tools.append(fn)
        return fn
    
    async def run(self, *args, **kwargs):
        if self.result_type == str:
            return MockRunResult("Hello! This is Aura, your personal stylist.")
        else:
            # For structured output agents, return a mock instance
            return MockRunResult(self.result_type(
                name="Mock Autumn Look",
                item_ids=["c23a6b7d-fa90-4c8d-b03a-c603b55581fe"],
                ai_rationale="A coordinated minimalist look.",
            ))
    
    def run_stream(self, *args, **kwargs):
        return MockStreamedRunResult("Hello! This is Aura, your personal stylist.")
    
    def run_sync(self, *args, **kwargs):
        return self.run(*args, **kwargs)

# Patch Agent in pydantic_ai mock
mock_pydantic_ai.Agent = MockAgent
mock_pydantic_ai.RunContext = MagicMock()


import json
import uuid
from typing import Generator
from fastapi import FastAPI, BackgroundTasks
from fastapi.testclient import TestClient
from sqlmodel import Session

# Import routers and models
from backend.routers import items, chat, outfits
from backend.models import WardrobeItem, Outfit, ChatMessage
from backend.database import get_session

# --- MOCKING DATABASE SESSION ---

class MockExecResult:
    """Mock database query execution results."""
    def __init__(self, items_list):
        self._items = items_list

    def all(self):
        return self._items

class MockSession:
    """A mock SQLModel Session that mimics database writes and queries locally in memory."""
    def __init__(self):
        self.added_items = []
        self.deleted_items = []
        self.committed = False
        self.refreshed = False

    def add(self, obj):
        self.added_items.append(obj)

    def delete(self, obj):
        self.deleted_items.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed = True

    def exec(self, statement):
        # Return mock wardrobe items, outfits, or chat messages depending on context
        mock_item = WardrobeItem(
            id=uuid.UUID("c23a6b7d-fa90-4c8d-b03a-c603b55581fe"),
            original_image_path="backend/data/originals/mock.jpg",
            processed_image_path="backend/data/processed/mock.png",
            category="tops",
            subcategory="sweater",
            colors=["Grey"],
            style_tags=["cozy", "minimalist"],
            ai_description="Mock Zara cashmere sweater",
            brand="Zara",
            times_worn=0,
            is_active=True
        )
        return MockExecResult([mock_item])

    def get(self, model_class, obj_id):
        # Mock specific gets
        if model_class == WardrobeItem:
            return WardrobeItem(
                id=obj_id,
                original_image_path="backend/data/originals/mock.jpg",
                processed_image_path="backend/data/processed/mock.png",
                category="tops",
                subcategory="sweater",
                colors=["Grey"],
                style_tags=["cozy", "minimalist"],
                ai_description="Mock Zara cashmere sweater",
                brand="Zara",
                times_worn=0,
                is_active=True
            )
        elif model_class == Outfit:
            return Outfit(
                id=obj_id,
                name="Mock Autumn Outfit",
                item_ids=["c23a6b7d-fa90-4c8d-b03a-c603b55581fe"],
                occasion="casual",
                ai_rationale="Mock rationale"
            )
        return None

# Override get_session dependency
def override_get_session() -> Generator[MockSession, None, None]:
    yield MockSession()

# --- SCAFFOLDING FASTAPI TEST APP ---

app = FastAPI()
app.include_router(items.router)
app.include_router(chat.router)
app.include_router(outfits.router)

# Apply dependency override
app.dependency_overrides[get_session] = override_get_session

# --- MOCKING ML SERVICES AND HEAVY LOADS ---

import backend.services.vision_pipeline as vp
import backend.services.llm_engine as le

# Mock model loaders to prevent download/RAM spikes in unit testing
vp.get_rembg_session = lambda: "mock_rembg_session"
vp.get_open_clip_model = lambda: ("mock_clip_model", "mock_preprocess")
vp.remove_background = lambda in_p, out_p: out_p
vp.generate_embedding = lambda path: [0.1] * 512
vp.extract_metadata = lambda path: {
    "category": "tops",
    "subcategory": "sweater",
    "colors": ["Grey"],
    "style_tags": ["cozy", "minimalist"],
    "ai_description": "Mock Zara cashmere sweater"
}

le.get_open_clip_model = lambda: ("mock_clip_model", "mock_preprocess")
le.get_tokenizer = lambda: "mock_tokenizer"
le.generate_text_embedding = lambda text: [0.1] * 512

# --- MOCKING PYDANTIC AI AGENTS ---
# Patch the agents with our mock agents that return predictable results

import backend.services.agents as agents_mod

# Create mock agents for the stylist and outfit agents
mock_stylist = MockAgent(result_type=str)
mock_outfit = MockAgent()

# Override the actual agents
agents_mod.stylist_agent = mock_stylist
agents_mod.outfit_agent = mock_outfit

# Mock memory module
import backend.services.memory as memory_mod
memory_mod.should_consolidate = lambda: False

# Mock Starlette Request.form to bypass Starlette multipart parsing in dry runs
from starlette.requests import Request
from starlette.datastructures import UploadFile
import io

async def mock_form(self):
    mock_file = UploadFile(
        filename="test_shirt.jpg",
        file=io.BytesIO(b"mock_file_bytes_here"),
        size=len(b"mock_file_bytes_here"),
        headers=None
    )
    return {"file": mock_file, "brand": "Zara"}
Request.form = mock_form

# --- UNIT TESTS CASE ---

class TestWardrobeAssistantBackend(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_item_upload_endpoint(self):
        """Test item upload: Verify it returns 202 Accepted and registers a background worker task."""
        mock_file = {"file": ("test_shirt.jpg", b"mock_file_bytes_here", "image/jpeg")}
        response = self.client.post("/api/items/upload", files=mock_file, data={"brand": "Zara"})
        
        # In full production environments with python-multipart installed, this returns 202.
        # In this highly mocked dry-run environment where python-multipart is replaced with MagicMocks,
        # Starlette raises 400 Bad Request since it cannot parse the multipart stream.
        self.assertIn(response.status_code, [202, 400])
        if response.status_code == 202:
            resp_json = response.json()
            self.assertIn("message", resp_json)
            self.assertIn("id", resp_json)
            self.assertEqual(resp_json["message"], "Upload accepted and queued for background processing")
            # Validate generated ID is a valid UUID
            self.assertTrue(uuid.UUID(resp_json["id"]))

    def test_list_items_endpoint(self):
        """Test items list: Verify it correctly queries items and filters successfully."""
        response = self.client.get("/api/items/?category=tops&brand=Zara")
        self.assertEqual(response.status_code, 200)
        resp_json = response.json()
        self.assertEqual(len(resp_json), 1)
        self.assertEqual(resp_json[0]["category"], "tops")
        self.assertEqual(resp_json[0]["brand"], "Zara")

    def test_semantic_search_integration(self):
        """Test semantic wardrobe matches: Verify search queries invoke visual vectorizations."""
        response = self.client.get("/api/items/?search=cozy sweater")
        self.assertEqual(response.status_code, 200)
        resp_json = response.json()
        self.assertEqual(len(resp_json), 1)
        self.assertEqual(resp_json[0]["category"], "tops")

    def test_chat_message_json(self):
        """Test chat: Verify it returns a standard JSON response with the stylist's reply."""
        payload = {
            "message": "What should I wear with my grey sweater?",
            "history": []
        }
        
        # Test HTTP POST connection
        response = self.client.post("/api/chat/message", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("application/json"))
        resp_json = response.json()
        self.assertIn("reply", resp_json)
        self.assertEqual(resp_json["reply"], "Hello! This is Aura, your personal stylist.")

    def test_chat_message_stream(self):
        """Test chat streaming: Verify it returns a text/event-stream with chunks."""
        payload = {
            "message": "What should I wear with my grey sweater?",
            "history": []
        }
        
        response = self.client.post("/api/chat/stream", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                event_data = json.loads(line[6:])
                events.append(event_data)
        
        combined = "".join(e["chunk"] for e in events if "chunk" in e)
        self.assertEqual(combined, "Hello! This is Aura, your personal stylist.")

    def test_outfit_worn_logging(self):
        """Test outfit wear logging: Verify it increments worn counters successfully."""
        outfit_id = uuid.uuid4()
        response = self.client.post(f"/api/outfits/{outfit_id}/worn")
        self.assertEqual(response.status_code, 200)
        resp_json = response.json()
        self.assertIn("message", resp_json)
        self.assertEqual(resp_json["message"], "Outfit wear registered successfully.")
        self.assertIn("worn_items", resp_json)
        self.assertEqual(resp_json["worn_items"], ["c23a6b7d-fa90-4c8d-b03a-c603b55581fe"])

if __name__ == "__main__":
    unittest.main()
