# AI SRE Copilot

An educational scaffold for evidence-based incident investigation. In this first stage, the system takes synthetic events and displays them on a timeline. It does not make changes to any systems, and it does not yet connect to an AI model or use RAG.

## Why Python and JSON?

This is a small, local project, so it uses Python and only the standard library. JSON keeps the events easy to read and process without a server or database. All records use ISO 8601 timestamps in UTC (`Z`), so events from different sources can be compared without time zone ambiguity.

## Project structure

- `data/incidents/payment-api.json` — a deterministic incident scenario containing logs, metrics, and a deployment event.
- `src/ai_sre_copilot/timeline.py` — loads and validates the scenario, then displays its events in chronological order.
- `tests/test_timeline.py` — checks timestamp formatting and event ordering.

## Run

Python 3.10 or later is required. From the repository directory, run:

```sh
python3 -m src.ai_sre_copilot.timeline
```

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The tests verify that each event has a valid UTC timestamp, that the scenario includes logs, metrics, and a deployment, and that the timeline is in chronological order.

## Scenario

The `payment-api` service is deployed at 12:04:30 UTC. After the deployment, the error rate rises and latency increases. The events are synthetic and fixed, so every run shows the same evidence.

## Next step

Add a consistent format for separate data sources, then build an analysis layer that explains the timing relationships among deployments, metrics, and logs. The system can remain read-only when an AI component is added later.
