"""Video storage service for persistent video upload and retrieval.

Manages video files on disk under storage/videos/ so they survive
backend restarts and page reloads.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Set

from config import VIDEOS_DIR
from domain.models import Sample
from services.dataset_service import dataset_service

logger = logging.getLogger(__name__)

ALLOWED_VIDEO_EXTENSIONS: Set[str] = {".mp4", ".webm", ".mov", ".mkv", ".avi"}
MAX_VIDEO_SIZE_BYTES: int = 150 * 1024 * 1024  # 150 MB limit


class VideoService:
    """Handles disk operations and persistence for generated videos."""

    def __init__(self, videos_dir: Path = VIDEOS_DIR) -> None:
        self._videos_dir = videos_dir
        self._videos_dir.mkdir(parents=True, exist_ok=True)

    def is_allowed_extension(self, filename: str) -> bool:
        """Check if filename has a permitted video extension."""
        suffix = Path(filename).suffix.lower()
        return suffix in ALLOWED_VIDEO_EXTENSIONS

    def get_video_path(self, filename: str) -> Path:
        """Get absolute path to stored video file."""
        return self._videos_dir / filename

    def save_uploaded_video(
        self,
        sample_id: str,
        original_filename: str,
        file_bytes: bytes,
    ) -> Optional[Sample]:
        """
        Save video bytes to storage/videos/{sample_id}{ext} and update sample state.

        Args:
            sample_id: Identifier of the target sample.
            original_filename: Filename from user upload.
            file_bytes: Binary contents of video file.

        Returns:
            Updated Sample or None if operation failed.
        """
        if not self.is_allowed_extension(original_filename):
            logger.warning(
                "Upload rejected: %s is not an allowed extension (%s)",
                original_filename,
                ALLOWED_VIDEO_EXTENSIONS,
            )
            return None

        if len(file_bytes) > MAX_VIDEO_SIZE_BYTES:
            logger.warning("Upload rejected: file size exceeds %d bytes", MAX_VIDEO_SIZE_BYTES)
            return None

        ext = Path(original_filename).suffix.lower() or ".mp4"
        dest_filename = f"{sample_id}{ext}"
        dest_path = self._videos_dir / dest_filename

        try:
            with open(dest_path, "wb") as f:
                f.write(file_bytes)
            logger.info("Saved video for %s to %s", sample_id, dest_path)
            return dataset_service.attach_video(sample_id, dest_filename)
        except Exception as err:
            logger.error("Failed to write video file %s: %s", dest_path, err)
            return None

    def delete_video(self, sample_id: str) -> Optional[Sample]:
        """Delete stored video file and update sample state."""
        sample = dataset_service.get_sample_by_id(sample_id)
        if not sample or not sample.video_filename:
            return sample

        target_file = self._videos_dir / sample.video_filename
        if target_file.exists():
            try:
                target_file.unlink()
                logger.info("Deleted video file %s", target_file)
            except Exception as err:
                logger.error("Error deleting file %s: %s", target_file, err)

        return dataset_service.remove_video(sample_id)


video_service = VideoService()
