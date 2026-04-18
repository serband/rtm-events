# Insurance PAS Architecture: Temporal Graph Specification

## Overview
This document outlines the architecture for the RTM Replacement project. Unlike traditional state-based insurance systems, this platform uses an **Event-Sourced Graph Architecture**. 

Every business fact is stored as an immutable event. The system projects these events into a **Graph Model** where People, Assets, and Policies are connected by time-aware relationships.

---

## 1. Core Architecture: The "Meta-Container"
The **Policy Container** is the root aggregate. It serves as the permanent anchor for all related insurance business.

- **Storage:** All events are indexed by `container_id`.
- **Identity:** The container holds the human-readable `policy_number`.
- **Portfolio Logic:** The container acts as the "Brain," coordinating multiple policy types (e.g., Motor, Home, Pet) under one account.

---

## 2. Node Schemas (The "Nouns")
Nodes represent the entities involved in the insurance lifecycle.

### **Person Schema**
Represents individuals or entities.
- **Identity:** Name, DOB, Contact details.
- **Risk Profile:** Driving history, license info, and claims history.
- **Roles:** A single person can hold multiple roles (Payer, Policyholder, Driver) across different policies in the container.

### **Asset Schema (e.g., Vehicle)**
Represents the insured objects.
- **Identification:** VIN, VRM, Year, Make, Model.
- **Risk Attributes:** Parking location, security features, modifications.
- **Genericity:** The structure is modular; swapping the `specification` block allows for Home, Pet, or Marine assets.

### **Insurance Policy Schema**
Represents a specific product contract.
- **Header:** Inception/Expiry dates and status.
- **Financials:** Granular breakdown of Net Premium, Tax (IPT), and Commissions.
- **Terms:** Versioned references to policy wordings and endorsements.

---

## 3. The Relationship Graph (The "Verbs")
The "Magic" of this system lies in the **Relationship Link**. Relationships are nodes themselves that connect other nodes.

- **Temporal Links:** Every relationship (e.g., "John drives the Tesla") has an `effective_from` and `effective_to` date.
- **Interconnectivity:**
    - **Person ↔ Person:** Spouse, Child, Employee.
    - **Person ↔ Asset:** Main Driver, Occasional Driver, Registered Keeper.
    - **Person ↔ Policy:** Policyholder, Beneficiary.
    - **Policy ↔ Asset:** Covered Item.

---

## 4. How Events Build the Graph
We do not update tables. We append events. To determine the "Current State," the system replays the lifecycle events:

1. **`RelationshipStarted`**: Creates a link between two nodes (e.g., adding a driver to a car).
2. **`AttributeChanged`**: Updates a node's data (e.g., changing an address) while preserving the old version.
3. **`RelationshipTerminated`**: Ends a link (e.g., removing a driver) without deleting the history.

---

## 5. Summary of Benefits
- **Auditability:** Every change to the "web" of relationships is timestamped and attributed.
- **Time-Travel:** Query the system "As-At" any date to see the exact family/asset configuration that existed then.
- **Flexibility:** Add new assets or family members without altering the core database schema.