"""Unit tests for DatasetService.

Validates boundary conditions (points < 15), deterministic extraction quotas,
filtering, pagination, and persistent state updates.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

# Ensure packages directory is on sys.path
PACKAGES_DIR = Path(__file__).resolve().parent.parent / "packages"
if PACKAGES_DIR.exists() and str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

from domain.models import SampleStatus
from services.dataset_service import dataset_service


class TestDatasetService(unittest.TestCase):
    """Test suite for DatasetService operations."""

    def test_samples_extracted_and_bounded(self) -> None:
        """Verify that samples are extracted and all satisfy counting_answer < 15."""
        samples = dataset_service.get_all_samples()
        self.assertGreater(len(samples), 0, "Samples should not be empty")

        for sample in samples:
            self.assertGreater(
                sample.counting_answer,
                0,
                f"Sample {sample.id} has invalid 0 count",
            )
            self.assertLess(
                sample.counting_answer,
                15,
                f"Sample {sample.id} exceeds boundary condition: {sample.counting_answer} >= 15",
            )
            self.assertEqual(
                len(sample.points),
                sample.counting_answer,
                f"Sample {sample.id} points length must match counting_answer",
            )

    def test_category_sample_quotas(self) -> None:
        """Verify that categories do not exceed target quota of 50 samples."""
        stats = dataset_service.get_project_stats()
        for cat in stats.categories:
            self.assertLessEqual(
                cat.total_samples,
                50,
                f"Category {cat.name} exceeds max quota of 50: {cat.total_samples}",
            )
            self.assertGreater(
                cat.total_samples,
                0,
                f"Category {cat.name} has no samples",
            )

    def test_filter_by_category(self) -> None:
        """Verify filtering by specific category works accurately."""
        color_samples = dataset_service.filter_samples(category="color")
        self.assertEqual(len(color_samples), 50)
        for s in color_samples:
            self.assertEqual(s.category_type, "color")

    def test_filter_by_search_query(self) -> None:
        """Verify filtering by text search query."""
        results = dataset_service.filter_samples(search_query="pen")
        self.assertGreater(len(results), 0)
        for s in results:
            match = (
                "pen" in s.description.lower()
                or "pen" in s.target_class.lower()
                or "pen" in s.image_filename.lower()
            )
            self.assertTrue(match, f"Sample {s.id} did not match search query 'pen'")

    def test_pagination(self) -> None:
        """Verify pagination slicing and total count."""
        all_samples = dataset_service.get_all_samples()
        page_items, total = dataset_service.paginate_samples(all_samples, page=1, page_size=10)
        self.assertEqual(len(page_items), 10)
        self.assertEqual(total, len(all_samples))

    def test_script_update_lifecycle(self) -> None:
        """Verify that updating a script transitions status to SCRIPTED."""
        samples = dataset_service.get_all_samples()
        sample = samples[0]

        updated = dataset_service.update_script(
            sample_id=sample.id,
            script="Test generated script content",
            disappear_cnt=2,
            appear_cnt=1,
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.script, "Test generated script content")
        self.assertEqual(updated.script_params.disappear_cnt, 2)
        self.assertEqual(updated.script_params.appear_cnt, 1)
        self.assertIn(updated.status, [SampleStatus.SCRIPTED, SampleStatus.VIDEO_UPLOADED])


if __name__ == "__main__":
    unittest.main()
