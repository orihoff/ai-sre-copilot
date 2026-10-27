"""Deterministic, explainable correlations across incident evidence."""

from datetime import timedelta
from typing import Any

from .timeline import parse_timestamp


def correlate_evidence(
    scenario: dict[str, Any], *, window_seconds: int = 300
) -> list[dict[str, Any]]:
    """Apply small rule-based checks; findings describe timing, not causation."""
    if window_seconds < 0:
        raise ValueError("window_seconds must be non-negative")

    events = scenario["events"]
    entities = {entity["id"]: entity for entity in scenario["entities"]}
    findings: list[dict[str, Any]] = []
    window = timedelta(seconds=window_seconds)

    def nearby(left: dict[str, Any], right: dict[str, Any]) -> bool:
        return abs(parse_timestamp(left["timestamp"]) - parse_timestamp(right["timestamp"])) <= window

    metrics = [event for event in events if event["type"] == "metric"]
    deployments = [event for event in events if event["type"] == "deployment"]

    # A same-entity, same-metric baseline and increase bracketing a deployment.
    for after in metrics:
        if after.get("direction") != "higher_is_worse" or not isinstance(after.get("value"), (int, float)):
            continue
        for deployment in deployments:
            if deployment["entity_id"] != after["entity_id"] or parse_timestamp(deployment["timestamp"]) >= parse_timestamp(after["timestamp"]):
                continue
            if not nearby(deployment, after):
                continue
            before_candidates = [
                event for event in metrics
                if event.get("direction") == "higher_is_worse"
                and event["entity_id"] == after["entity_id"]
                and event.get("name") == after.get("name")
                and isinstance(event.get("value"), (int, float))
                and parse_timestamp(event["timestamp"]) < parse_timestamp(deployment["timestamp"])
                and nearby(event, deployment)
            ]
            if not before_candidates:
                continue
            before = max(before_candidates, key=lambda e: parse_timestamp(e["timestamp"]))
            if after["value"] <= before["value"]:
                continue
            findings.append({
                "rule": "metric_increase_after_deployment",
                "summary": (
                    f"{after['entity_id']} {after['name']} increased from "
                    f"{before['value']} to {after['value']} {after.get('unit', '')} "
                    f"within {window_seconds}s after deployment {deployment.get('version', '')}."
                ).strip(),
                "evidence_event_ids": [before["id"], deployment["id"], after["id"]],
            })

    # A service timeout explicitly linked to a declared dependency, bracketed by
    # an increase in that dependency's latency.
    for log in events:
        dependency_id = log.get("related_entity_id")
        if log["type"] != "log" or log.get("severity") != "error" or not dependency_id:
            continue
        if dependency_id not in entities[log["entity_id"]].get("depends_on", []):
            continue
        if "timeout" not in log.get("message", "").lower():
            continue
        dependency_metrics = [
            event for event in metrics
            if event["entity_id"] == dependency_id and event.get("name") == "p95_latency"
            and event.get("direction") == "higher_is_worse"
            and isinstance(event.get("value"), (int, float))
        ]
        before_candidates = [
            event for event in dependency_metrics
            if parse_timestamp(event["timestamp"]) < parse_timestamp(log["timestamp"])
            and nearby(event, log)
        ]
        after_candidates = [
            event for event in dependency_metrics
            if parse_timestamp(event["timestamp"]) > parse_timestamp(log["timestamp"])
            and nearby(event, log)
        ]
        if not before_candidates or not after_candidates:
            continue
        before = max(before_candidates, key=lambda e: parse_timestamp(e["timestamp"]))
        after = min(after_candidates, key=lambda e: parse_timestamp(e["timestamp"]))
        if after["value"] <= before["value"]:
            continue
        findings.append({
            "rule": "dependency_timeout_with_latency_increase",
            "summary": (
                f"{log['entity_id']} logged a timeout for dependency {dependency_id}; "
                f"its p95 latency increased from {before['value']} to {after['value']} "
                f"{after.get('unit', '')} around that event."
            ).strip(),
            "evidence_event_ids": [before["id"], log["id"], after["id"]],
        })

    return findings
