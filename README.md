# AI SRE Copilot

An educational project for investigating service incidents using evidence from logs, metrics, and deployments. The current version loads one deterministic, synthetic incident and prints its events in time order. It is read-only: it does not connect to production systems or change anything. It does not use an AI model or RAG yet.

## How the project works

The incident is stored as JSON so it is easy to inspect and change. Each event has an ISO 8601 timestamp in UTC (`Z`) and a type: `log`, `metric`, or `deployment`. The timeline module validates the event types and timestamps, sorts events chronologically, and prints a compact summary. Python's standard library handles this, so no service, database, or third-party package is needed.

![Project flow: scenario JSON is validated, sorted, then printed as a timeline. Tests check the input and ordering.](docs/diagrams/project-flow.svg)

The diagram source is editable in [diagrams.net](https://app.diagrams.net/) using [project-flow.drawio](docs/diagrams/project-flow.drawio).

## Synthetic incident walkthrough

The example follows `payment-api` around deployment version `1.8.2`. The 5xx rate is 0.2% before the deployment. After the deployment, an inventory timeout appears in the logs, the 5xx rate rises to 8.4%, p95 latency reaches 2400 ms, and another payment request fails after retries.

![Incident evidence timeline: baseline metric, deployment, timeout, elevated errors and latency, then failed payment request.](docs/diagrams/incident-timeline.svg)

The timeline makes the sequence easy to inspect, but timing alone does not prove that the deployment caused the errors. The diagram source is editable in diagrams.net using [incident-timeline.drawio](docs/diagrams/incident-timeline.drawio).

## Project structure

- `data/incidents/payment-api.json` — deterministic sample evidence: logs, metrics, and a deployment event.
- `src/ai_sre_copilot/timeline.py` — loads and validates the scenario, sorts events, and prints the timeline.
- `tests/test_timeline.py` — verifies that all evidence types are present, timestamps are UTC, and sorted output is chronological.
- `docs/diagrams/` — editable diagrams.net source files and SVG versions displayed above.

## Run

Requires Python 3.10 or later. From the repository directory:

```sh
python3 -m src.ai_sre_copilot.timeline
```

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Next step

Add support for loading multiple evidence files through one shared event format. Then build an analysis layer that links related log lines, metric changes, and deployments, while showing the supporting evidence for each explanation. An AI model or RAG can be considered later; any explanation should remain evidence-based, and the system should stay read-only.
