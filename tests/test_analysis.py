from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analyse_droughts.py"
SPEC = importlib.util.spec_from_file_location("analyse_droughts", SCRIPT)
analysis = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = analysis
SPEC.loader.exec_module(analysis)


class AnalysisTests(unittest.TestCase):
    def observation(self, day: int, flow: float | None, accepted: bool = True):
        return analysis.Observation(
            day=date(2000, 1, day),
            flow=flow,
            accepted=accepted,
            good_only=accepted,
            quality="Good" if accepted else "Missing",
            completeness="Complete" if accepted else "Incomplete",
        )

    def test_percentile_uses_linear_interpolation(self):
        self.assertAlmostEqual(analysis.percentile([1.0, 2.0, 3.0, 4.0], 0.25), 1.75)

    def test_missing_day_censors_adjacent_events(self):
        observations = [
            self.observation(1, 0.5),
            self.observation(2, 0.1),
            self.observation(3, None, accepted=False),
            self.observation(4, 0.1),
            self.observation(5, 0.5),
        ]
        events = analysis.identify_events(observations, threshold=0.2, screen="accepted")
        self.assertEqual(len(events), 2)
        self.assertTrue(events[0]["right_censored"])
        self.assertTrue(events[1]["left_censored"])

    def test_pooling_does_not_cross_invalid_gap(self):
        observations = [
            self.observation(1, 0.5),
            self.observation(2, 0.1),
            self.observation(3, None, accepted=False),
            self.observation(4, 0.1),
            self.observation(5, 0.5),
        ]
        events = analysis.identify_events(observations, threshold=0.2, screen="accepted")
        pooled = analysis.pool_events(events, observations, screen="accepted")
        self.assertEqual(len(pooled), 2)

    def test_pooling_merges_short_valid_interruption(self):
        observations = [
            self.observation(1, 0.5),
            self.observation(2, 0.1),
            self.observation(3, 0.3),
            self.observation(4, 0.1),
            self.observation(5, 0.5),
        ]
        events = analysis.identify_events(observations, threshold=0.2, screen="accepted")
        pooled = analysis.pool_events(events, observations, screen="accepted")
        self.assertEqual(len(pooled), 1)
        self.assertEqual(pooled[0]["duration_days"], 3)


if __name__ == "__main__":
    unittest.main()
