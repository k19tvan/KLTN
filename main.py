"""Main entry point for REC-8K Video Generation Tracker.

Starts the FastAPI server, mounts static assets, serves images and videos,
and hosts the visualization web interface.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add packages directory to sys.path
PACKAGES_DIR = Path(__file__).resolve().parent / "packages"
if PACKAGES_DIR.exists() and str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router as api_router
from config import REC8K_IMAGES_DIR, VIDEOS_DIR, config

app = FastAPI(
    title="REC-8K Video Transformation Tracker",
    description="Track and visualize REC-8K sample curation, LLM 6s scripting, and video persistence.",
    version="1.0.0",
)

# Enable CORS for local workflows
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API
app.include_router(api_router)

# Mount media directories
if REC8K_IMAGES_DIR.exists():
    app.mount("/media/images", StaticFiles(directory=str(REC8K_IMAGES_DIR)), name="images")

VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media/videos", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")

# Mount frontend static files
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index() -> FileResponse:
    """Serve the single-page application interface."""
    index_file = STATIC_DIR / "index.html"
    return FileResponse(str(index_file))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        reload=False,
    )
