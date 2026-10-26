"""Load, validate, and render an application's incident evidence timeline."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCENARIO_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "incidents" / "payment-api.json"
)
EVENT_TYPES = {"log", "metric", "deployment"}
ENTITY_KINDS = {"service", "component"}


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 UTC timestamp and reject timestamps without UTC."""
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"timestamp must use UTC Z suffix: {value}")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"timestamp must be UTC: {value}")
    return parsed


def validate_scenario(scenario: dict[str, Any]) -> None:
    """Validate the application, entity graph, and evidence records."""
    if not isinstance(scenario, dict) or not scenario.get("scenario"):
        raise ValueError("scenario must include a scenario name")
    application = scenario.get("application")
    if (
        not isinstance(application, dict)
        or not isinstance(application.get("id"), str)
        or not application["id"].strip()
        or not isinstance(application.get("name"), str)
        or not application["name"].strip()
    ):
        raise ValueError("scenario must include an application with an id and name")

    entities = scenario.get("entities")
    if not isinstance(entities, list) or not entities:
        raise ValueError("scenario must include at least one service or component")
    entities_by_id: dict[str, dict[str, Any]] = {}
    for entity in entities:
        if not isinstance(entity, dict):
            raise ValueError("each entity must be an object")
        entity_id = entity.get("id")
        if (
            not isinstance(entity_id, str)
            or not entity_id.strip()
            or not isinstance(entity.get("name"), str)
            or not entity["name"].strip()
        ):
            raise ValueError("each entity must include an id and name")
        if entity_id in entities_by_id:
            raise ValueError(f"duplicate entity id: {entity_id}")
        if entity.get("kind") not in ENTITY_KINDS:
            raise ValueError(f"unsupported entity kind for {entity_id}: {entity.get('kind')}")
        entities_by_id[entity_id] = entity

    for entity in entities:
        dependencies = entity.get("depends_on", [])
        if not isinstance(dependencies, list):
            raise ValueError(f"dependencies for {entity['id']} must be a list")
        for dependency in dependencies:
            if not isinstance(dependency, str):
                raise ValueError(f"dependency IDs for {entity['id']} must be strings")
            if dependency not in entities_by_id:
                raise ValueError(
                    f"unknown dependency {dependency!r} for entity {entity['id']}"
                )

    events = scenario.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("scenario must contain at least one event")
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("each event must be an object")
        event_type = event.get("type")
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported event type: {event_type}")
        if event.get("entity_id") not in entities_by_id:
            raise ValueError(f"event references unknown entity: {event.get('entity_id')}")
        parse_timestamp(event.get("timestamp"))
    if {event["type"] for event in events} != EVENT_TYPES:
        raise ValueError("scenario must contain log, metric, and deployment events")


def load_scenario(path: Path = SCENARIO_PATH) -> dict[str, Any]:
    """Load and validate a scenario from a JSON file."""
    scenario = json.loads(path.read_text(encoding="utf-8"))
    validate_scenario(scenario)
    return scenario


def chronological_events(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a new event list ordered by timestamp, preserving ties."""
    return sorted(scenario["events"], key=lambda event: parse_timestamp(event["timestamp"]))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print a synthetic incident's evidence in chronological order."
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        type=Path,
        default=SCENARIO_PATH,
        help=f"path to a scenario JSON file (default: {SCENARIO_PATH.name})",
    )
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    entities = {entity["id"]: entity for entity in scenario["entities"]}
    application = scenario["application"]
    print(f"Application: {application['name']}")
    print(f"Scenario: {scenario['scenario']}")
    for event in chronological_events(scenario):
        entity_name = entities[event["entity_id"]]["name"]
        summary = event.get("message") or event.get("name") or ""
        if event["type"] == "deployment":
            summary = f"version {event['version']} to {event['environment']}"
        elif "value" in event:
            summary = f"{summary}={event['value']} {event.get('unit', '')}".rstrip()
        print(
            f"{event['timestamp']}  {event['type']:<10} "
            f"{entity_name}: {summary}"
        )


if __name__ == "__main__":
    main()
