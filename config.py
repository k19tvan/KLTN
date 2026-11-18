"""Application configuration module.

Loads environment variables, defines filesystem paths, and provides
strongly-typed configuration settings following PEP 8 and Clean Code standards.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Ensure workspace packages directory is available in sys.path
_PACKAGES_DIR = Path(__file__).resolve().parent / "packages"
if _PACKAGES_DIR.exists() and str(_PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGES_DIR))

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Dataset constants
REC8K_DIR = (BASE_DIR / "../dataset/REC-8K").resolve()
REC8K_ANNOTATIONS_PATH = REC8K_DIR / "annotations.json"
REC8K_IMAGES_DIR = REC8K_DIR / "images"

# Application storage paths
STORAGE_DIR = BASE_DIR / "storage"
VIDEOS_DIR = STORAGE_DIR / "videos"
DATASET_STORE_PATH = STORAGE_DIR / "dataset.json"

# Extraction constants
SAMPLES_PER_TYPE_TARGET = 50
MAX_POINTS_ALLOWED = 15  # Points must be strictly smaller than 15 (< 15)
RANDOM_SEED = 42

# Video transformation constants
VIDEO_DURATION_SECONDS = 6


@dataclass(frozen=True)
class AppConfig:
    """Immutable application runtime settings."""

    # LLM Configuration
    llm_base_url: str = os.getenv("BASE_URL", os.getenv("OPENAI_BASE_URL", "http://localhost:8000/v1"))
    llm_api_key: str = os.getenv("API_KEY", os.getenv("OPENAI_API_KEY", "EMPTY"))
    llm_model_name: str = os.getenv("MODEL_NAME", os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"))

    # Server Configuration
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT", "8000"))

    # Storage paths
    dataset_path: Path = REC8K_ANNOTATIONS_PATH
    images_dir: Path = REC8K_IMAGES_DIR
    storage_dir: Path = STORAGE_DIR
    videos_dir: Path = VIDEOS_DIR
    dataset_store_path: Path = DATASET_STORE_PATH


config = AppConfig()
