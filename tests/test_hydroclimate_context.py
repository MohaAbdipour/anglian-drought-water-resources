import sys
import unittest
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyse_hydroclimate_context import (  # noqa: E402
    antecedent_total,
    groundwater_month_percentile,
    nearest_groundwater,
    percentile_rank,
)


class HydroclimateContextTests(unittest.TestCase):
    def test_percentile_rank_uses_midrank_for_ties(self):
        self.assertEqual(percentile_rank(2.0, [1.0, 2.0, 2.0, 4.0]), 50.0)

    def test_antecedent_total_excludes_event_start(self):
        anchor = date(2020, 1, 5)
        rainfall = {anchor - timedelta(days=i): float(i) for i in range(5)}
        self.assertEqual(antecedent_total(rainfall, anchor, 3), 6.0)

    def test_antecedent_total_rejects_incomplete_window(self):
        with self.assertRaises(ValueError):
            antecedent_total({date(2020, 1, 1): 1.0}, date(2020, 1, 3), 2)

    def test_nearest_groundwater_applies_offset_limit(self):
        readings = [
            {"date": date(2020, 1, 1), "value": 10.0, "quality": "Good"},
            {"date": date(2020, 4, 1), "value": 11.0, "quality": "Good"},
        ]
        found = nearest_groundwater(readings, date(2020, 1, 20), 45)
        self.assertEqual(found["offset_days"], -19)
        self.assertIsNone(nearest_groundwater(readings, date(2020, 2, 20), 10))

    def test_groundwater_percentile_uses_same_month_reference(self):
        readings = []
        for year in range(1991, 2021):
            readings.append({"date": date(year, 7, 1), "value": float(year), "quality": "Good"})
            readings.append({"date": date(year, 8, 1), "value": 999.0, "quality": "Good"})
        percentile, count = groundwater_month_percentile(2005.0, 7, readings)
        self.assertEqual(count, 30)
        self.assertAlmostEqual(percentile, 48.3333333333)


if __name__ == "__main__":
    unittest.main()
