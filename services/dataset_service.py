"""Dataset service for REC-8K sampling, querying, and state persistence.

Handles extraction of samples with < 15 points, deterministic curation of 50 samples
per type, and atomic reads/writes to persistent storage.
"""

from __future__ import annotations

import json
import logging
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import (
    DATASET_STORE_PATH,
    MAX_POINTS_ALLOWED,
    RANDOM_SEED,
    REC8K_ANNOTATIONS_PATH,
    SAMPLES_PER_TYPE_TARGET,
    STORAGE_DIR,
    VIDEOS_DIR,
)
from domain.models import (
    CategorySummary,
    ProjectStats,
    Sample,
    SampleStatus,
    ScriptParams,
)

logger = logging.getLogger(__name__)


def _sanitize_slug(text: str) -> str:
    """Convert arbitrary text into a filesystem and URL-safe slug."""
    clean = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", clean)


def _generate_sample_id(category: str, image_filename: str, description: str) -> str:
    """Generate a deterministic, readable unique identifier for a sample."""
    img_stem = Path(image_filename).stem
    desc_slug = _sanitize_slug(description)
    return f"{category}_{img_stem}_{desc_slug}"


def _get_utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class DatasetService:
    """Manages REC-8K samples extraction, lifecycle, and persistence."""

    def __init__(
        self,
        annotations_path: Path = REC8K_ANNOTATIONS_PATH,
        storage_path: Path = DATASET_STORE_PATH,
    ) -> None:
        self._annotations_path = annotations_path
        self._storage_path = storage_path
        self._samples: Dict[str, Sample] = {}
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Ensure directories exist and load or initialize sample data."""
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

        if self._storage_path.exists():
            self._load_from_storage()
        else:
            self._extract_and_persist_initial_dataset()

    def _load_from_storage(self) -> None:
        """Load curated samples from existing persistent JSON file."""
        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            self._samples = {
                item["id"]: Sample.model_validate(item) for item in raw_data
            }
            logger.info("Loaded %d samples from %s", len(self._samples), self._storage_path)
        except Exception as err:
            logger.error("Failed to load dataset from %s: %s", self._storage_path, err)
            self._extract_and_persist_initial_dataset()

    def _save_to_storage(self) -> None:
        """Persist current samples in memory to JSON store atomically."""
        data = [sample.model_dump() for sample in self._samples.values()]
        temp_path = self._storage_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(self._storage_path)

    def _extract_and_persist_initial_dataset(self) -> None:
        """Parse raw REC-8K annotations and extract 50 samples per category."""
        if not self._annotations_path.exists():
            logger.warning("REC-8K annotations file not found at %s", self._annotations_path)
            self._samples = {}
            return

        with open(self._annotations_path, "r", encoding="utf-8") as f:
            raw_annotations: Dict[str, Dict[str, dict]] = json.load(f)

        # Group candidates by category type with points < MAX_POINTS_ALLOWED
        categorized_candidates: Dict[str, List[dict]] = {}

        for img_name, descriptions in raw_annotations.items():
            for desc_text, info in descriptions.items():
                points = info.get("points", [])
                point_count = len(points)
                if 0 < point_count < MAX_POINTS_ALLOWED:
                    category = info.get("type", "unknown").strip().lower()
                    if category not in categorized_candidates:
                        categorized_candidates[category] = []
                    categorized_candidates[category].append(
                        {
                            "image_filename": img_name,
                            "description": desc_text,
                            "category_type": category,
                            "target_class": info.get("class", ""),
                            "attribute": info.get("attribute", ""),
                            "counting_answer": point_count,
                            "points": points,
                        }
                    )

        # Deterministic sampling of up to SAMPLES_PER_TYPE_TARGET for each category
        rng = random.Random(RANDOM_SEED)
        now_str = _get_utc_now_iso()
        extracted: Dict[str, Sample] = {}

        for category, candidates in sorted(categorized_candidates.items()):
            # Sort first for deterministic shuffling
            candidates.sort(key=lambda c: (c["image_filename"], c["description"]))
            rng.shuffle(candidates)
            selected = candidates[:SAMPLES_PER_TYPE_TARGET]

            for item in selected:
                sample_id = _generate_sample_id(
                    item["category_type"],
                    item["image_filename"],
                    item["description"],
                )
                sample = Sample(
                    id=sample_id,
                    image_filename=item["image_filename"],
                    description=item["description"],
                    category_type=item["category_type"],
                    target_class=item["target_class"],
                    attribute=item["attribute"],
                    counting_answer=item["counting_answer"],
                    points=item["points"],
                    script_params=ScriptParams(disappear_cnt=1, appear_cnt=0),
                    script=None,
                    video_filename=None,
                    status=SampleStatus.PENDING,
                    created_at=now_str,
                    updated_at=now_str,
                )
                extracted[sample_id] = sample

        self._samples = extracted
        self._save_to_storage()
        logger.info(
            "Extracted %d samples across %d categories into %s",
            len(self._samples),
            len(categorized_candidates),
            self._storage_path,
        )

    def get_sample_by_id(self, sample_id: str) -> Optional[Sample]:
        """Retrieve a single sample by its unique ID."""
        return self._samples.get(sample_id)

    def get_all_samples(self) -> List[Sample]:
        """Return all samples in memory."""
        return list(self._samples.values())

    def filter_samples(
        self,
        category: Optional[str] = None,
        status: Optional[SampleStatus] = None,
        search_query: Optional[str] = None,
    ) -> List[Sample]:
        """Filter samples by category type, status, and description text."""
        result = list(self._samples.values())

        if category and category.lower() != "all":
            cat_lower = category.lower()
            result = [s for s in result if s.category_type.lower() == cat_lower]

        if status:
            result = [s for s in result if s.status == status]

        if search_query:
            query = search_query.lower().strip()
            result = [
                s
                for s in result
                if query in s.description.lower()
                or query in s.target_class.lower()
                or query in s.image_filename.lower()
            ]

        return result

    def paginate_samples(
        self,
        samples: List[Sample],
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Sample], int]:
        """Paginate a pre-filtered list of samples. Returns (page_items, total_count)."""
        total = len(samples)
        start_idx = max(0, (page - 1) * page_size)
        end_idx = min(total, start_idx + page_size)
        return samples[start_idx:end_idx], total

    def update_sample(self, sample: Sample) -> Sample:
        """Update sample data and persist to storage."""
        sample.updated_at = _get_utc_now_iso()
        self._samples[sample.id] = sample
        self._save_to_storage()
        return sample

    def update_script(
        self,
        sample_id: str,
        script: str,
        disappear_cnt: int,
        appear_cnt: int,
    ) -> Optional[Sample]:
        """Update the generated script and parameters for a sample."""
        sample = self._samples.get(sample_id)
        if not sample:
            return None

        sample.script = script
        sample.script_params = ScriptParams(
            disappear_cnt=disappear_cnt,
            appear_cnt=appear_cnt,
        )
        if sample.status == SampleStatus.PENDING:
            sample.status = SampleStatus.SCRIPTED

        return self.update_sample(sample)

    def attach_video(self, sample_id: str, video_filename: str) -> Optional[Sample]:
        """Attach an uploaded video file to a sample and mark as uploaded."""
        sample = self._samples.get(sample_id)
        if not sample:
            return None

        sample.video_filename = video_filename
        sample.status = SampleStatus.VIDEO_UPLOADED
        return self.update_sample(sample)

    def remove_video(self, sample_id: str) -> Optional[Sample]:
        """Detach video from sample and revert status."""
        sample = self._samples.get(sample_id)
        if not sample:
            return None

        sample.video_filename = None
        sample.status = (
            SampleStatus.SCRIPTED if sample.script else SampleStatus.PENDING
        )
        return self.update_sample(sample)

    def get_project_stats(self) -> ProjectStats:
        """Calculate system-wide and category-level metrics."""
        categories_map: Dict[str, Dict[str, int]] = {}

        total_scripted = 0
        total_video = 0

        for s in self._samples.values():
            cat = s.category_type
            if cat not in categories_map:
                categories_map[cat] = {"total": 0, "scripted": 0, "video": 0}

            categories_map[cat]["total"] += 1
            if s.script:
                categories_map[cat]["scripted"] += 1
                total_scripted += 1
            if s.video_filename:
                categories_map[cat]["video"] += 1
                total_video += 1

        category_summaries = [
            CategorySummary(
                name=cat,
                total_samples=stats["total"],
                scripted_samples=stats["scripted"],
                video_uploaded_samples=stats["video"],
            )
            for cat, stats in sorted(categories_map.items())
        ]

        return ProjectStats(
            total_samples=len(self._samples),
            total_categories=len(category_summaries),
            scripted_count=total_scripted,
            video_uploaded_count=total_video,
            categories=category_summaries,
        )


# Global singleton instance for the dataset service
dataset_service = DatasetService()
