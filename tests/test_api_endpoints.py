"""End-to-end API integration tests for REC-8K Video Studio.

Tests all REST endpoints: statistics, category filters, script generation,
video file upload and persistence, and media streaming.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

PACKAGES_DIR = Path(__file__).resolve().parent.parent / "packages"
if PACKAGES_DIR.exists() and str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

from starlette.testclient import TestClient
from main import app
from services.dataset_service import dataset_service


class TestAPIEndpoints(unittest.TestCase):
    """Integration test suite for FastAPI REST API endpoints."""

    def setUp(self) -> None:
        self.client = TestClient(app)
        samples = dataset_service.get_all_samples()
        self.sample = samples[0]

    def test_get_stats(self) -> None:
        """Verify GET /api/stats returns valid schema and positive sample counts."""
        res = self.client.get("/api/stats")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_samples", data)
        self.assertGreater(data["total_samples"], 0)
        self.assertIn("categories", data)

    def test_get_categories(self) -> None:
        """Verify GET /api/categories returns a list of category summaries."""
        res = self.client.get("/api/categories")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_get_samples_with_filters(self) -> None:
        """Verify GET /api/samples pagination and category filtering."""
        res = self.client.get("/api/samples?category=action&page=1&page_size=10")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 10)
        self.assertLessEqual(len(data["samples"]), 10)
        for s in data["samples"]:
            self.assertEqual(s["category_type"], "action")

    def test_generate_script_endpoint(self) -> None:
        """Verify POST /api/samples/{id}/script generates and stores script."""
        payload = {"disappear_cnt": 1, "appear_cnt": 1}
        res = self.client.post(f"/api/samples/{self.sample.id}/script", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("script", data)
        self.assertGreater(len(data["script"]), 50)
        self.assertEqual(data["disappear_cnt"], 1)
        self.assertEqual(data["appear_cnt"], 1)

    def test_video_upload_and_delete_flow(self) -> None:
        """Verify complete video ingestion, persistence, and cleanup flow."""
        fake_video_bytes = b"\x00\x00\x00 ftypmp42\x00\x00\x00\x00mp42isom"
        files = {"file": ("test_clip.mp4", fake_video_bytes, "video/mp4")}

        # 1. Upload
        res_upload = self.client.post(f"/api/samples/{self.sample.id}/video", files=files)
        self.assertEqual(res_upload.status_code, 200)
        uploaded = res_upload.json()
        self.assertEqual(uploaded["status"], "video_uploaded")
        self.assertIsNotNone(uploaded["video_filename"])

        # 2. Verify static serving
        res_stream = self.client.get(f"/media/videos/{uploaded['video_filename']}")
        self.assertEqual(res_stream.status_code, 200)
        self.assertEqual(res_stream.content, fake_video_bytes)

        # 3. Delete
        res_delete = self.client.delete(f"/api/samples/{self.sample.id}/video")
        self.assertEqual(res_delete.status_code, 200)
        cleaned = res_delete.json()
        self.assertIsNone(cleaned["video_filename"])

    def test_serve_index_html(self) -> None:
        """Verify GET / serves the interactive single-page app HTML."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("REC-8K Video Transformation Studio", res.text)


if __name__ == "__main__":
    unittest.main()
