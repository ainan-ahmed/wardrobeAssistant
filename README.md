# 👗 wardrobeAssistant
>
> **A local-first, AI-powered personal wardrobe manager featuring automatic cloth-segmentation background removal, semantic fashion lookalike searches, and an interactive conversational style therapist.**

---

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Mantine UI](https://img.shields.io/badge/Mantine_UI-v7-339AF0?style=for-the-badge&logo=mantine)](https://mantine.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-Extension-1f2937?style=for-the-badge)](https://github.com/pgvector/pgvector)

---

## 🛠️ The Tech Stack

This project is built to showcase production-grade local AI desktop engineering, offline image segmentation, and high-performance vector retrieval inside a single-user application.

| Component | Technology | Rationale & Architectural Fit |
| :--- | :--- | :--- |
| **Background Isolation** | **`rembg` (u2net_cloth_seg)** | Fast, offline image-matting model fine-tuned for clothing. Extracts clean, transparent apparel cutouts directly on your machine without relying on external cloud endpoints. |
| **Semantic Vectorization** | **`open_clip` (Marqo-FashionSigLIP)** | Domain-specific SigLIP vision-text model trained specifically on fashion aspects. Converts clothes pictures and text queries into normalized **512-dimensional embeddings** for high-precision style retrieval. |
| **Vision & Generation** | **Gemini 2.5 Flash** | Advanced multimodal LLM routed via **`litellm`**. Automatically catalogs clothes by generating structured JSON metadata (colors, categories, styles) and generates streaming fashion suggestions. |
| **Backend & ORM** | **FastAPI & SQLModel** | High-performance asynchronous backend. SQLModel unifies Pydantic validation and SQLAlchemy queries into single-source schemas with native **`pgvector`** dialect integration. |
| **Database** | **PostgreSQL + pgvector** | Solid PostgreSQL backend running in a **local Docker container**. The `pgvector` extension allows transactional relational metadata queries combined with high-dimensional similarity searches. |
| **Desktop Wrapper** | **`pywebview`** | Lightweight native GUI shell that wraps the FastAPI backend and React static app, providing a clean, standalone desktop application experience. |
| **Frontend UI** | **React & Mantine v7** | Sleek editorial interface utilizing Mantine components. Built with auto-switching light/dark color schemes, warm closet aesthetics, and smooth CSS transitions. |

---

## 🏗️ Technical Architecture & Ingestion Lifecycle

To maintain high desktop responsiveness, `wardrobeAssistant` implements a **multi-threaded asynchronous architecture**. Large model imports and network processing are isolated to prevent freezing the interface.

1. **Dual-Thread Shell:** On execution, `backend/main.py` launches the FastAPI server in a dedicated background worker thread while starting the OS native `pywebview` client frame on the main thread.
2. **Asynchronous Ingestion Pipeline:** When a user drops an image, the backend immediately returns a `222 Accepted` response. The image is queued into a FastAPI background task which runs background isolation (`rembg`), metadata parsing (`Gemini`), and vector embedding generation (`OpenCLIP`) in parallel.
3. **Semantic Lookalike queries:** Text queries or outfit contexts are converted to vector vectors using OpenCLIP and matched against clothing embeddings in the database using pgvector's `<=>` cosine similarity operator.

---

## 📖 Developer Documentation

To aid developers and AI coding assistants in understanding the codebase architecture, setup details, and pipeline internals, the following supplementary guides are available:

*   **[WORKFLOW.md](file:///home/ainan/Projects/wardrobeAssistant/WORKFLOW.md):** A deep-dive detailing process startup, double-threaded shells, lazy runtime singleton model loads, asynchronous background ingestion tasks, vector similarity search queries, and RAG style streams.
*   **[AGENT.md](file:///home/ainan/Projects/wardrobeAssistant/AGENT.md):** Essential context guidelines, exact CLI commands for running local services, and architectural execution flow rules compiled for assistant agents.

