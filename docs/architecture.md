# RTM Replacement Architecture

## Purpose

This document is the canonical architecture for the RTM replacement POC.

It resolves the current ambiguity between:

- a traditional PAS that updates mutable policy rows
- an event-sourced temporal graph that preserves every business fact

The chosen direction is the second one.

## Design Principles

- Every business change is recorded as an immutable event.
- Current state is a projection, not the source of truth.
- Time-aware relationships are first-class, not implicit foreign keys.
- Portfolio complexity is normal, not an edge case.
- Product-specific detail lives in typed payloads, not hard-coded tables for every attribute.

## Domain Model

### 1. Policy Container

The `PolicyContainer` is the long-lived account envelope.

It exists to group all insurance business that belongs to the same customer context:

- portfolios
- parties
- assets
- policies
- cross-policy relationships

The container is the stable anchor for audit, reconstruction, and customer-level querying.

### 2. Portfolio

`Portfolio` is a logical grouping inside a container.

Examples:

- annual motor portfolio
- short-term motorcycle portfolio
- home and contents portfolio

For this POC, portfolio should be treated as a node owned by the container, not as a separate top-level aggregate with its own persistence boundary. It exists to organize policies and allow one customer to hold multiple product families simultaneously.

### 3. Nodes

The graph contains these node types:

- `Party`
- `Asset`
- `Policy`
- `Portfolio`

#### Party

Represents a person or legal entity.

Common data:

- identity
- contact details
- risk profile details
- role eligibility

A single party can appear across multiple policies and multiple roles over time.

#### Asset

Represents an insured object.

Current asset families in scope:

- motor vehicle
- motorcycle
- home property

The asset envelope should be generic, with product-specific specification blocks. 

Example shape:

```json
{
  "asset_id": "AST-001",
  "asset_type": "motorcycle",
  "identification": {
    "vin": "EK71TDY",
    "registration_number": "AB12CDE"
  },
  "specification": {
    "make": "Triumph",
    "model": "Street Triple",
    "engine_cc": 765,
    "year_of_manufacture": 2024
  },
  "risk_attributes": {
    "garaging_postcode": "SW1A 1AA",
    "security_devices": ["immobiliser"]
  }
}
```

#### Policy

Represents one insurance contract for one insured asset.

Policy data should include items such as:

- product type (motor, motorcycle, home, contents)
- status
- start date + time
- policy duration 
- end date
- NCD or NCB details where applicable
- legal protection
- premium and tax details

Constraint for this POC:

- every policy must be linked to exactly one asset

That is a domain invariant. It should be enforced on the write side once the plumbing phase is complete.

## Relationships

Relationships are first-class graph edges with temporal validity.

Each relationship must carry:

- `relationship_id`
- `relationship_type`
- `from_node_id`
- `to_node_id`
- `role`
- `context_policy_id` when relevant
- `effective_from`
- `effective_to`

Examples:

- party to policy: `Policyholder`
- party to policy: `Payer`
- party to asset: `MainDriver`
- party to asset: `NamedDriver`
- party to party: `Spouse`
- policy to asset: `Covers`
- portfolio to policy: `Contains`

Important rule:

- do not encode relationships only inside node JSON

The graph edge is the business fact. Read models may denormalize it later.

## Aggregate Boundaries

This is the main design decision that keeps the model coherent.

### Target write model

Use separate aggregates for durable business entities:

- `PolicyContainer`
- `Policy`
- `Party`
- `Asset`
- `Relationship`

### Why not keep everything inside one container aggregate?

Because a single aggregate holding all mutable dictionaries causes three problems:

- unrelated changes compete on one event stream
- event names become generic and low value
- temporal reconstruction becomes harder because the event payloads look like patches instead of business facts

### Responsibility of each aggregate

`PolicyContainer`:

- opens the customer envelope
- creates portfolios
- records membership references
- coordinates cross-entity registration when needed

`Policy`:

- owns contract lifecycle
- owns product terms and premium timeline
- owns link to exactly one asset

`Party`:

- owns party identity and risk profile history

`Asset`:

- owns asset specification and risk attribute history

`Relationship`:

- owns the temporal life of a graph edge

This separation gives cleaner streams, cleaner projections, and better time-travel behavior.

## Event Model

Events should describe business facts, not generic CRUD-style mutation.

### Container events

- `ContainerOpened`
- `PortfolioAddedToContainer`
- `PartyRegisteredInContainer`
- `AssetRegisteredInContainer`
- `PolicyRegisteredInContainer`

These events establish membership and identity references.

### Policy events

- `PolicyCreated`
- `PolicyActivated`
- `PolicyStatusChanged`
- `PolicyAssetLinked`
- `PolicyTermAdjusted`
- `PolicyPremiumAdjusted`
- `PolicyCancelled`
- `PolicyRenewed`
- `PolicyLapsed`
- `PolicyLegalProtectionChanged`
- `PolicyNoClaimsDiscountChanged`

### Party events

- `PartyCreated`
- `PartyIdentityUpdated`
- `PartyContactUpdated`
- `PartyRiskProfileUpdated`

### Asset events

- `AssetCreated`
- `VehicleSpecificationUpdated`
- `MotorcycleSpecificationUpdated`
- `HomeSpecificationUpdated`
- `AssetRiskAttributesUpdated`

### Relationship events

- `RelationshipStarted`
- `RelationshipEnded`
- `RelationshipBackdated`

For most cases, a relationship should not be "updated" in place. End the old one and start a new one.

## JSON Schemas To Event Streams

JSON schemas define payload shape. They do not define persistence strategy.

The mapping should be:

- schema describes the structure of a command or event payload
- command decides intent
- aggregate validates and emits one or more events
- event store persists those events
- projector builds read models from the events

Example:

Input command:

```json
{
  "policy_id": "POL-1001",
  "party_id": "PTY-2001",
  "asset_id": "AST-3001",
  "role": "MainDriver",
  "effective_from": "2026-04-14"
}
```

This should not result in a SQL `UPDATE policy SET drivers = ...`.

It should result in an appended event such as:

```json
{
  "event_type": "RelationshipStarted",
  "aggregate_type": "Relationship",
  "aggregate_id": "REL-4001",
  "payload": {
    "relationship_type": "party_to_asset",
    "from_node_id": "PTY-2001",
    "to_node_id": "AST-3001",
    "role": "MainDriver",
    "context_policy_id": "POL-1001",
    "effective_from": "2026-04-14",
    "effective_to": null
  }
}
```

That event is immutable. If the driver is later removed, append `RelationshipEnded`. If replaced, end the old relationship and start a new one.

## PostgreSQL As Event Store

PostgreSQL is not the domain model. It is the durable append-only persistence layer for events.

Conceptually, the event store table contains rows like:

- aggregate id
- aggregate type
- version
- event type
- event payload
- event timestamp
- causation id
- correlation id

Illustrative shape:

```sql
CREATE TABLE stored_events (
    originator_id UUID NOT NULL,
    originator_version BIGINT NOT NULL,
    topic TEXT NOT NULL,
    state BYTEA NOT NULL,
    PRIMARY KEY (originator_id, originator_version)
);
```

With the `eventsourcing` library, the framework manages the low-level storage format and optimistic concurrency. PostgreSQL gives you:

- durable append-only storage
- transactional writes
- ordering within a stream by version
- replay support
- snapshot support if introduced later

What it does not do by itself:

- graph semantics
- business invariants
- read-model shape

Those remain application responsibilities.

## Mid-Term Adjustments

An MTA is a new business fact, not an overwrite.

Example:

- Monday: policy premium is 1062.00 and legal protection is false
- Tuesday: legal protection is added and premium becomes 1168.20

The write side appends events on Tuesday, for example:

- `PolicyLegalProtectionChanged`
- `PolicyPremiumAdjusted`

Tuesday does not destroy Monday. Monday remains reconstructable by replaying only the events known up to that time or version.

## Time Travel And As-At Queries

Two different concepts matter here:

### Event-sourcing time travel

Rehydrate an aggregate at:

- a specific version
- a specific timestamp if supported by repository/query strategy

This proves historical truth for one stream.

### Read-model as-at query

Project the graph as it stood on a date or datetime by applying temporal filtering:

- include only relationships effective at that moment
- include only attribute versions known by that moment
- include only policy terms active at that moment

For the PAS, most UI and reporting needs will use read-model as-at queries, while debugging and audit will also use raw aggregate replay.

## Read Model Strategy

The write model and read model should be deliberately different.

Write side:

- aggregate streams
- immutable events
- consistency boundaries

Read side:

- denormalized query tables
- graph views
- policy timelines
- portfolio summaries

Suggested read projections:

- `container_summary`
- `portfolio_summary`
- `policy_current_view`
- `policy_timeline`
- `party_current_view`
- `asset_current_view`
- `relationship_current_view`
- `relationship_history`

The projector is allowed to mutate read tables because those are disposable derived models.

## Product Extensibility

The core graph should remain product-agnostic while allowing typed detail per product family.

Recommended pattern:

- stable envelope fields common to all assets and policies
- product-specific `specification` or `terms` payload blocks
- event names that are explicit when the product family matters

Examples:

- `MotorcycleSpecificationUpdated`
- `HomeSpecificationUpdated`

This avoids turning the whole platform into a lowest-common-denominator schema while still preserving extensibility.

## POC Invariants

These are the important invariants for the next implementation phase:

- every policy belongs to one container
- every policy belongs to one portfolio
- every policy links to exactly one asset
- a party can have many roles across many policies
- relationships are time-aware
- history is append-only

Business validations such as "must have a primary driver" are intentionally deferred.

## Recommended Next Refactor

Refactor the current Python implementation toward this target:

1. Stop using generic `PolicyUpdated`, `PartyUpdated`, and `AssetUpdated` as primary write events.
2. Move policy, party, asset, and relationship history into separate aggregate streams.
3. Keep the container as the membership and coordination anchor.
4. Make relationship lifecycle explicit with `Started` and `Ended` events.
5. Drive "as-at" behavior from event replay and temporal projections, not only from filtered in-memory dictionaries.
