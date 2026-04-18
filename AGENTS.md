Role: Senior Insurance Systems Architect & Python Developer
Objective: Build a Proof of Concept (POC) for a modern, Event-Sourced Policy Administration System (PAS) to replace a 30-year-old legacy system (RTM).

1. The Logic Framework (The Graph)
We are using a Temporal Graph Architecture. Please implement the following hierarchy:

Meta Policy Container: The root aggregate (The "Envelope").

Portfolio: A logical grouping inside the container that can hold multiple Insurance Policies (e.g., Annual Motor, Short-term Motorcycle, Home).

Nodes: * Parties: (People/Entities) with identity and risk data.

Assets: (Vehicles/Motorcycles) with identification and specification data.

Relationships (The Edges): Time-aware links that connect People to Assets (e.g., "Main Driver"), People to Policies ("Policyholder"), and People to People ("Spouse").

2. Data Requirements & Schemas
Every policy must be linked to exactly one asset. We need to expand our JSON schemas to include:

Policy Details: NCD (No Claims Discount), Legal Protection, Start Date, and Policy Duration.

Motorcycle Asset: Similar to our Vehicle schema (VIN, Make, Model) but tailored for bikes.

Relationships: Must support effective_from and effective_to dates.

3. The "Events" Challenge (Primary Task)
I need to understand how we turn these JSON schemas into an Event Sourcing system. Please:

Explain how a PostgreSQL database acts as the "Event Store."

Show how an action (like "Adding a Driver") is stored as an immutable Event rather than a table update.

Provide a Python example using the eventsourcing library that demonstrates a Mid-Term Adjustment (MTA): show the "As-At" state of a policy on Monday, change an attribute on Tuesday, and then "Time Travel" back to Monday to prove the original data is still there.

4. Constraints

Do not worry about business validation rules yet (e.g., "Must have a primary driver"). Focus on the plumbing of the events and the graph links.

The system must be able to handle "Portfolio" complexity where one person has multiple assets and policies.