# RTM Replacement POC

Proof of concept for a modern Policy Administration System to replace RTM using an event-sourced temporal graph rather than mutable policy records.

## Intent

The system is being designed to support UK insurance products with portfolio complexity:

- one customer container holding multiple policies
- one person participating in multiple policies and roles
- one person linked to multiple assets over time
- one asset linked to exactly one policy at a time
- full auditability and "as-at" reconstruction

The current codebase contains a mix of older state-centric ideas and newer event-sourced graph ideas. The canonical direction is now defined in the architecture documents below.

## Canonical Documents

- [Architecture](/Users/serban/Documents/RTM%20-%20events/docs/architecture.md)
- [Current State And Gaps](/Users/serban/Documents/RTM%20-%20events/docs/current-state-and-gaps.md)
- [Schema Explained](/Users/serban/Documents/RTM%20-%20events/JSON%20Schemas/Schema_Explained.md)

## Core Model

- `PolicyContainer` is the durable account envelope and root business boundary.
- `Portfolio` is a logical grouping inside the container, not a separate billing account.
- `Party`, `Asset`, and `Policy` are graph nodes.
- `Relationship` is time-aware and first-class.
- The write side stores immutable events.
- The read side projects those events into query models for UI, reporting, and integration.

## Immediate Scope

This POC is focused on plumbing, not full insurance business rules:

- temporal graph structure
- event store pattern
- PostgreSQL-backed event sourcing
- mid-term adjustments
- as-at and time-travel queries
- motor, motorcycle, and home-ready extensibility

## Run The Playground

Launch the Streamlit UI with:

```bash
.venv/bin/streamlit run streamlit_app.py
```

The playground uses a local SQLite event store at `streamlit_playground.db` and keeps a lightweight container catalog in `playground_catalog.json` so you can reopen previously created containers from the sidebar.

Use the `Generate Complex Scenario` button in the sidebar to create a richer seeded household with multiple portfolios, policies, parties, assets, relationships, and a small MTA/history trail. The generated scenario blueprint is also shown in the overview tab so the underlying JSON is visible.

## Out Of Scope For Now

- rating logic
- underwriting validations
- document production
- bordereaux and downstream finance detail
- full broker workflow orchestration

## Project Layout

- [streamlit_app.py](/Users/serban/Documents/RTM%20-%20events/streamlit_app.py): interactive playground
- [scenario_generator.py](/Users/serban/Documents/RTM%20-%20events/scenario_generator.py): seeded scenario blueprints
- [application.py](/Users/serban/Documents/RTM%20-%20events/application.py): application service and snapshots
- [domain.py](/Users/serban/Documents/RTM%20-%20events/domain.py): event-sourced aggregates
- [projector.py](/Users/serban/Documents/RTM%20-%20events/projector.py): simple read-model projection example
- [tests](/Users/serban/Documents/RTM%20-%20events/tests): lifecycle, scenario, and generator coverage
