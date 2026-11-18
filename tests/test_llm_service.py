"""Unit tests for LLM script generation service.

Validates the create_script function signature, timeline prompt structure,
and boundary condition handling.
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

PACKAGES_DIR = Path(__file__).resolve().parent.parent / "packages"
if PACKAGES_DIR.exists() and str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

from services.llm_service import create_script


class TestLLMService(unittest.TestCase):
    """Test suite for 6-second video script generation."""

    def test_create_script_signature_and_output(self) -> None:
        """Verify create_script returns a comprehensive 6-second script."""
        script = create_script(
            image="0000-fsc147-1106.jpg",
            description="purple pen",
            disappear_cnt=1,
            appear_cnt=0,
        )
        self.assertIsInstance(script, str)
        self.assertGreater(len(script), 50)
        self.assertIn("purple pen", script)

    def test_boundary_conditions_negative_counts(self) -> None:
        """Verify negative counts are sanitized without breaking."""
        script = create_script(
            image="test.jpg",
            description="blue ball",
            disappear_cnt=-3,
            appear_cnt=-1,
        )
        self.assertIsInstance(script, str)
        self.assertIn("blue ball", script)

    def test_dynamic_appearance_and_disappearance(self) -> None:
        """Verify script reflects dynamic changes in the timeline prompt."""
        script = create_script(
            image="test_sample.jpg",
            description="red cup",
            disappear_cnt=2,
            appear_cnt=3,
        )
        self.assertIn("2", script)
        self.assertIn("3", script)
        self.assertIn("red cup", script)


if __name__ == "__main__":
    unittest.main()
