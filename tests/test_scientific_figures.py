import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from make_scientific_figures import moving_mean  # noqa: E402


class ScientificFigureTests(unittest.TestCase):
    def test_moving_mean_retains_supported_window(self):
        result = moving_mean([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        self.assertEqual(result, [1.5, 2.0, 3.0, 4.0, 4.5])

    def test_moving_mean_does_not_bridge_sparse_window(self):
        result = moving_mean([1.0, None, None, 4.0, None], 3)
        self.assertIsNone(result[2])


if __name__ == "__main__":
    unittest.main()
