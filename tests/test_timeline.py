import unittest
from pathlib import Path

from src.ai_sre_copilot.timeline import (
    chronological_events,
    load_scenario,
    parse_timestamp,
)


class TimelineTests(unittest.TestCase):
    def setUp(self):
        scenario_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "incidents"
            / "payment-api.json"
        )
        self.scenario = load_scenario(scenario_path)

    def test_scenario_contains_all_evidence_types(self):
        self.assertEqual(
            {event["type"] for event in self.scenario["events"]},
            {"log", "metric", "deployment"},
        )

    def test_timestamps_are_utc_and_events_are_chronological(self):
        events = chronological_events(self.scenario)
        timestamps = [parse_timestamp(event["timestamp"]) for event in events]

        self.assertTrue(all(timestamp.utcoffset().total_seconds() == 0 for timestamp in timestamps))
        self.assertEqual(timestamps, sorted(timestamps))

    def test_parser_rejects_timestamps_without_utc_suffix(self):
        with self.assertRaises(ValueError):
            parse_timestamp("2026-10-20T12:00:00")


if __name__ == "__main__":
    unittest.main()
