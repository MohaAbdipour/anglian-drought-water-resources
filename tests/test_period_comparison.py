from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_periods.py"
SPEC = importlib.util.spec_from_file_location("compare_periods", SCRIPT)
comparison = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = comparison
SPEC.loader.exec_module(comparison)


class PeriodComparisonTests(unittest.TestCase):
    def test_periods_are_equal_and_contiguous(self):
        bounds = list(comparison.PERIODS.values())
        self.assertTrue(all(end - start + 1 == 19 for start, end in bounds))
        self.assertEqual(bounds[0][1] + 1, bounds[1][0])
        self.assertEqual(bounds[1][1] + 1, bounds[2][0])

    def test_block_bootstrap_is_deterministic_for_fixed_seed(self):
        values = [1.0, 2.0, None, 4.0, 5.0, 6.0]
        first = comparison.block_bootstrap_means(values, seed=42, replicates=20)
        second = comparison.block_bootstrap_means(values, seed=42, replicates=20)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 20)

    def test_confidence_interval_is_ordered(self):
        low, high = comparison.confidence_interval([1.0, 2.0, 3.0, 4.0])
        self.assertLess(low, high)


if __name__ == "__main__":
    unittest.main()
