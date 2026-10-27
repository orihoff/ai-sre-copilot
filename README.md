# AI SRE Copilot

AI SRE Copilot is a small learning project for investigating incidents across an application and the services and components it depends on. It collects synthetic evidence into one timeline, then applies explainable rules to point out signals that happened near each other.

It currently reads a local JSON scenario only. It does not connect to production, change infrastructure, call an AI model, or use retrieval-augmented generation (RAG). The name describes the direction of the project; the current engine is deterministic Python code.

## What problem it demonstrates

An application may be made of multiple services and components. For example, a checkout application may call a payment service, which calls an inventory service and a database. During an incident, a symptom can appear in one place while a useful clue appears somewhere else:

1. A release is deployed to `payment-api`.
2. The payment service's error rate rises.
3. Its logs report a timeout to `inventory-api`.
4. Inventory latency rises around the same time.

The project puts these records in a shared application-level timeline and shows which records its rules linked. This makes it a starter for incident investigation across **services and components**, rather than a tool limited to one process or one service. A component can be a database, queue, cache, or other dependency.

![Project workflow: load and validate a scenario, build a timeline, correlate evidence, and print findings with event IDs.](docs/diagrams/project-flow.svg)

The workflow diagram can be edited in diagrams.net using [project-flow.drawio](docs/diagrams/project-flow.drawio).

## How the pieces fit together

1. **Scenario data** lives in [payment-api.json](data/incidents/payment-api.json). It describes an application, its entities and dependency links, and timestamped evidence.
2. **Validation and timeline rendering** are in [timeline.py](src/ai_sre_copilot/timeline.py). The loader checks required IDs and references, requires UTC timestamps, and sorts evidence across all entities.
3. **Correlation rules** are in [correlation.py](src/ai_sre_copilot/correlation.py). They compare related records and return a short explanation plus the event IDs used as evidence.
4. **The command-line interface** prints the timeline and correlation findings. It does not send or modify data outside the local process.

Python's standard library is sufficient; no database, external service, or third-party package is required.

## The sample incident

The example is a synthetic Checkout Platform incident. `payment-api` depends on `inventory-api` and `orders-db`; `inventory-api` depends on `inventory-db`. During the sample window, payment version `1.8.2` is deployed, payment error rate and latency increase, a payment log records an inventory timeout, and inventory latency rises. A later payment log records a failed request after retries.

![Timeline of the sample Checkout Platform incident across payment-api and inventory-api.](docs/diagrams/incident-timeline.svg)

The diagram source is editable in diagrams.net using [incident-timeline.drawio](docs/diagrams/incident-timeline.drawio). The scenario is deliberately small so each record and each correlation can be inspected by hand.

## Scenario data model

The JSON file has three main sections:

- **`application`** identifies the application with an `id` and a human-readable `name`.
- **`entities`** lists services and components. Each has a unique `id`, `name`, and `kind`. `depends_on` contains IDs of entities it calls or relies on. These links describe the architecture; they do not claim that a dependency caused an incident.
- **`events`** contains logs, metrics, and deployments. Every event has a unique `id`, `type`, `entity_id`, and UTC `timestamp` ending in `Z`.

Event-specific fields provide details. Logs can include `severity`, `message`, and `trace_id`. A log can also include `related_entity_id` to explicitly identify the dependency mentioned by the record. Metrics include `name`, numeric `value`, and `unit`; `direction: "higher_is_worse"` tells the engine that a larger value is a concerning change. Deployment records include `version` and `environment`.

For example, a metric on `inventory-api` and a timeout log on `payment-api` remain separate events, but both appear in the application timeline. The dependency relationship and the log's `related_entity_id` give the correlation rule structured information to connect them.

## Evidence Correlation Engine

The engine currently applies two explicit rules:

### 1. Metric increase after deployment

For a metric marked `higher_is_worse`, the engine looks for a baseline on an entity, a deployment to that same entity, and a higher value for the same metric after the deployment. The baseline and later measurement must each be within the configured time window of the deployment. Each finding cites the baseline metric, deployment, and later metric event IDs.

### 2. Dependency timeout with latency increase

The engine looks for an error log whose message contains “timeout” and whose `related_entity_id` is listed in the logging entity's `depends_on` field. It then looks for a baseline and a higher `p95_latency` metric on that dependency around the log time. A finding cites the baseline metric, timeout log, and later metric event IDs.

These checks are temporal correlations. They can help an investigator decide what to inspect next, but they do not prove causation. The current rules do not parse arbitrary log text to discover dependencies, calculate statistical significance, or establish that a metric change is operationally important. The engine only reports evidence already present in the scenario.

## Run it

Requires Python 3.10 or later. From the repository directory, run the bundled scenario:

```sh
python3 -m src.ai_sre_copilot.timeline
```

Pass a different scenario JSON file:

```sh
python3 -m src.ai_sre_copilot.timeline path/to/another-scenario.json
```

Set the maximum time gap used by the rules in seconds. The default is 300 seconds (five minutes):

```sh
python3 -m src.ai_sre_copilot.timeline --correlation-window 600
```

The output shows each event's timestamp, type, entity, and event ID. The correlation section lists each rule's summary and the IDs of the records it used. Use those IDs to find the original evidence in the JSON scenario.

## Tests

Run the automated tests with:

```sh
python3 -m unittest discover -s tests -v
```

The current tests load the valid sample scenario, check that it contains all three evidence types, and verify UTC timestamps and chronological ordering. They do not yet exercise the correlation rules or invalid input cases. Add focused cases for each rule, time-window boundaries, missing evidence, malformed references, and situations where no finding should be produced.

## Project structure

- [data/incidents/payment-api.json](data/incidents/payment-api.json) — synthetic application topology and incident evidence.
- [src/ai_sre_copilot/timeline.py](src/ai_sre_copilot/timeline.py) — input validation, sorting, and CLI output.
- [src/ai_sre_copilot/correlation.py](src/ai_sre_copilot/correlation.py) — deterministic evidence correlation rules.
- [tests/test_timeline.py](tests/test_timeline.py) — current validation and ordering tests.
- [docs/diagrams/](docs/diagrams/) — diagrams.net sources and SVG diagrams shown in this README.

## Suggested next steps

Grow the project in small steps, keeping each result explainable and runnable locally:

1. **Cover the engine with tests.** Check both rules, no-match cases, missing or malformed evidence, and events just inside and outside the time window. Test that every finding points to valid event IDs.
2. **Make the rules configurable.** Add explicit limits such as a minimum percentage increase or a latency threshold, and explain the chosen threshold in each finding. Keep metric units and directions consistent.
3. **Improve the finding format.** Add severity/confidence labels with clear definitions, and expose findings as JSON so another interface can consume them.
4. **Separate input sources.** Add small local-file adapters for logs, metrics, and deployment records, then normalize them into the existing scenario format. Start with fixture files rather than production credentials or live integrations.
5. **Add more evidence relationships.** For example, connect matching trace IDs, compare error rates with request volume, or include database and queue latency. Keep each rule deterministic and cite its inputs.
6. **Build a simple viewer.** Show the application dependency graph, timeline, and findings together, with a way to open the source records behind a finding.
7. **Consider AI/RAG later.** Once the data model and rules are reliable, an AI model could summarize already-collected evidence. Keep source citations visible, distinguish summaries from measured facts, and retain read-only behavior unless the project deliberately adds a separately reviewed action workflow.

The most useful immediate step is the first one: tests will make it safer to add thresholds and new evidence sources without changing what existing rules mean.
