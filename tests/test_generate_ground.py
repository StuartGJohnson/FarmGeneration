from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from orchard_generator.ground_generator import generate_ground_texture


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GROUND_TEXTURE_OUTPUT = PROJECT_ROOT / "assets" / "ground_plane.png"


class GenerateGroundTest(unittest.TestCase):
    def test_generate_ground_texture(self) -> None:
        generate_ground_texture(GROUND_TEXTURE_OUTPUT, size=2048, seed=42)

        self.assertTrue(GROUND_TEXTURE_OUTPUT.is_file())
        image = Image.open(GROUND_TEXTURE_OUTPUT)
        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.size, (2048, 2048))

        pixels = np.asarray(image)
        self.assertGreater(float(pixels.std()), 8.0)
        self.assertLess(float(pixels.std()), 55.0)


if __name__ == "__main__":
    unittest.main()
