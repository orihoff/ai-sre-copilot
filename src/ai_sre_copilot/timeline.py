"""Load and render the repository's deterministic incident scenario."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCENARIO_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "incidents" / "payment-api.json"
)
EVENT_TYPES = {"log", "metric", "deployment"}


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 UTC timestamp and reject timestamps without UTC."""
    if not value.endswith("Z"):
        raise ValueError(f"timestamp must use UTC Z suffix: {value}")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"timestamp must be UTC: {value}")
    return parsed


def load_scenario(path: Path = SCENARIO_PATH) -> dict[str, Any]:
    """Load a scenario and validate its required event types and timestamps."""
    scenario = json.loads(path.read_text(encoding="utf-8"))
    events = scenario["events"]
    if not events:
        raise ValueError("scenario must contain at least one event")
    for event in events:
        if event.get("type") not in EVENT_TYPES:
            raise ValueError(f"unsupported event type: {event.get('type')}")
        parse_timestamp(event["timestamp"])
    if {event["type"] for event in events} != EVENT_TYPES:
        raise ValueError("scenario must contain log, metric, and deployment events")
    return scenario


def chronological_events(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a new event list ordered by timestamp, preserving ties."""
    return sorted(scenario["events"], key=lambda event: parse_timestamp(event["timestamp"]))


def main() -> None:
    scenario = load_scenario()
    print(f"Scenario: {scenario['scenario']} ({scenario['service']})")
    for event in chronological_events(scenario):
        summary = event.get("message") or event.get("name") or event.get("version")
        if "value" in event:
            summary = f"{summary}={event['value']} {event['unit']}"
        print(f"{event['timestamp']}  {event['type']:<10} {summary}")


if __name__ == "__main__":
    main()
