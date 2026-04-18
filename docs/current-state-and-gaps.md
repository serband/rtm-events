# Current State And Gaps

## Why This Exists

The codebase already contains a workable proof of concept, but it does not yet consistently implement the target architecture.

This note explains the current state so the next coding phase is deliberate.

## What The Current Code Already Gets Right

- `PolicyContainer` exists as a root account envelope.
- events are persisted through the `eventsourcing` library
- there is a PostgreSQL-ready application layer
- temporal relationships have `effective_from` and `effective_to`
- there is an early projector/read-model pattern
- there is an initial MTA/time-travel demonstration

## Where The Current Code Is Still Transitional

### 1. Too much state lives inside one aggregate

In [domain.py](/Users/serban/Documents/RTM%20-%20events/domain.py), the container owns mutable dictionaries for:

- policies
- parties
- assets
- relationships

That is acceptable for a first sketch, but it is not the target model for a durable PAS. It centralizes unrelated changes into one stream and makes event semantics too generic.

### 2. Generic update events are too weak

The current events:

- `PolicyUpdated`
- `PartyUpdated`
- `AssetUpdated`

are patch-style events. They describe that something changed, but not what business fact occurred. That weakens audit clarity and complicates downstream projections.

### 3. Relationship is both embedded and aggregate-like

The code defines a `Relationship` aggregate, but relationships are also stored as dictionaries on the container. The architecture should choose one consistent write-side approach. The canonical direction is separate relationship streams plus projected container-level graph views.

### 4. The current MTA demo proves versions, not full as-at semantics

In [application.py](/Users/serban/Documents/RTM%20-%20events/application.py), the demonstration shows version-based reconstruction, which is useful. But the `get_container_state_as_of()` method is still a simplified filter over current in-memory state rather than a full event-time reconstruction.

### 5. The read model is ahead in some places and behind in others

In [projector.py](/Users/serban/Documents/RTM%20-%20events/projector.py), the read side already treats relationships as temporal and uses denormalized tables. That is the right direction. But the projections still depend on generic write events from the container, so the read model cannot yet express richer business history without additional translation.

## Practical Interpretation

The current prototype should be treated as:

- valid as a learning scaffold
- useful for proving the library and persistence setup
- not yet the final aggregate/event design

## What Should Happen Next

The next implementation phase should focus on architectural correction, not feature breadth:

1. normalize the write model around explicit business events
2. split entity history into proper streams
3. preserve the container as the account envelope
4. upgrade the MTA example to use policy-specific events
5. show true Monday-versus-Tuesday reconstruction with a clearer event timeline

## Short Rule Of Thumb

If a future code change feels like "update a JSON blob on the policy," it is probably still leaning back toward the legacy mindset.

If it feels like "record a new fact and let projections derive the state," it is probably aligned with the target architecture.
