# AI SRE Copilot

An educational project for investigating incidents across an application, its services, and their supporting components. The current version loads a deterministic, synthetic application scenario and prints evidence from multiple entities in time order. It is read-only: it does not connect to production systems or change anything. It does not use an AI model or RAG yet.

## How the project works

The incident is stored as JSON so it is easy to inspect and change. Each scenario describes an application, its entities, their dependencies, and the evidence events. An entity can be a **service** such as `payment-api` or a **component** such as a database. Each event points to the entity it describes and has an ISO 8601 UTC timestamp (`Z`) plus a type: `log`, `metric`, or `deployment`.

For example, `payment-api` can declare that it depends on `inventory-api` and `orders-db`. An event with `"entity_id": "inventory-api"` then places inventory evidence in the same application timeline, so investigators can compare related signals across the dependency graph.

The timeline module checks entity, dependency, and event IDs plus UTC timestamps, sorts all evidence by time, and prints each record with its entity name and event ID. The Evidence Correlation Engine then applies deterministic rules to those records. Python's standard library handles this, so no service, database, or third-party package is needed.

![Project flow: scenario JSON is validated, sorted, correlated, then printed with evidence references.](docs/diagrams/project-flow.svg)

The diagram source is editable in [diagrams.net](https://app.diagrams.net/) using [project-flow.drawio](docs/diagrams/project-flow.drawio).

## Synthetic incident walkthrough

The example application is the **Checkout Platform**. `payment-api` depends on `inventory-api` and `orders-db`; `inventory-api` depends on `inventory-db`. Around the deployment of payment version `1.8.2`, the timeline shows the payment service's 5xx rate rising from 0.2% to 8.4%, an inventory timeout, increased inventory latency, and payment latency reaching 2400 ms before a request fails after retries.

![Checkout Platform timeline showing payment-api deployment and errors alongside inventory-api latency evidence.](docs/diagrams/incident-timeline.svg)

The timeline makes the cross-service sequence easy to inspect. The correlation engine reports that payment 5xx rate and latency increased after the deployment, and that an inventory timeout coincided with increased inventory latency. These are temporal correlations, not proof that one event caused another. The diagram source is editable in diagrams.net using [incident-timeline.drawio](docs/diagrams/incident-timeline.drawio).

## Evidence Correlation Engine

The engine uses explicit, reviewable rules; it does not call an AI model or infer relationships from arbitrary text:

- **Metric increase after deployment:** finds a baseline and higher value for the same `higher_is_worse` metric on the deployed entity, within the configured time window.
- **Dependency timeout with latency increase:** checks an error log that names a declared dependency via `related_entity_id`, then looks for a higher `p95_latency` measurement on that dependency around the log time.

Every finding lists the source event IDs in time order. Metric records must set `direction` to `higher_is_worse` for the engine to compare them. Findings describe temporal associations and do not establish causation. The engine is read-only and only analyzes evidence already in the scenario file.

## Project structure

- `data/incidents/payment-api.json` — a deterministic application scenario with a service dependency graph and sample logs, metrics, and deployment evidence.
- `src/ai_sre_copilot/timeline.py` — loads and validates an application scenario, sorts events across entities, and prints the timeline and findings.
- `src/ai_sre_copilot/correlation.py` — applies the deterministic deployment and dependency correlation rules.
- `tests/test_timeline.py` — verifies that all evidence types are present, timestamps are UTC, and sorted output is chronological.
- `docs/diagrams/` — editable diagrams.net source files and SVG versions displayed above.

## Run

Requires Python 3.10 or later. From the repository directory:

```sh
python3 -m src.ai_sre_copilot.timeline
```

Pass another scenario file as an optional argument:

```sh
python3 -m src.ai_sre_copilot.timeline path/to/another-scenario.json
```

Change the correlation time window (default 300 seconds):

```sh
python3 -m src.ai_sre_copilot.timeline --correlation-window 600
```

## Tests

```sh
python3 -m unittest discover -s tests -v
```

## Next step

Next, add adapters that collect logs, metrics, and deployment records from separate local input files into this shared scenario format. The correlation rules can then be expanded with clear thresholds and additional evidence types. An AI model or RAG can be considered later; explanations should remain evidence-based, and the system should stay read-only.
