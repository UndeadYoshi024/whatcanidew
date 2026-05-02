# Dew — FHIR Integration Guide

This guide is for the IT professional deploying Dew in an Epic environment. It covers what Dew expects at runtime, how to configure dynamic constraint updates, and how the hospital's FHIR resources map to Dew's graph structure.

---

## What Dew Expects at Runtime

A JSON `POST` to `/route` containing:

- `intent` — the routing profile description you provided at setup (identical string, every time — this is how Dew retrieves the cached constraint profile)
- `graph` — an anonymous graph produced by the pre-configured sanitizer: node ids, connections, and optional edge weights
- `start` — the opaque identifier of the source node
- `target` — the opaque identifier of the destination node
- `caller` — a label for the log (e.g., `"epic_sanitizer"`)

No natural language at runtime beyond the cached intent string. No patient data. No FHIR resource structure. Just graph topology and routing parameters.

---

## Setup vs. Runtime

**Setup — once, by IT:**

Call `POST /synthesize` with a plain-language description of the routing use case. Dew's keyword parser reads your intent and shapes terrain: what to prefer, what to penalize, what to block entirely. The resulting constraint profile is written to the activity log and cached in memory.

```
POST /synthesize
{
  "intent": "route to nearest available room, prefer direct connections, block rooms under maintenance",
  "caller": "it_setup"
}
```

**Runtime — every chart-save or constraint change:**

The pre-configured sanitizer posts an anonymous graph to `/route`. Dew applies the cached constraint profile, runs Dijkstra, returns the path. No human intervention.

---

## Configuring Dynamic Constraint Updates

When a doctor's schedule changes, room availability changes, or any routing constraint changes, the graph needs to reflect it before the next routing call.

Configure a hospital intranet endpoint that:

1. Listens for constraint change events from Epic — Schedule changes, Slot availability changes, Location status changes.
2. Translates those events into updated graph instructions (same opaque identifiers the sanitizer uses).
3. Posts the updated graph to Dew on the next routing call.

IT configures this endpoint once. After that, constraint changes flow into the graph automatically. No manual intervention. No redeployment. No IT ticket.

The endpoint watches the relevant Epic data: Schedule resources when practitioner availability changes, Slot resources when appointment capacity changes, Location resources when room or bed status changes. When something changes, it sends an updated graph reflecting the new constraint. Dew receives it on the next `/route` call.

---

## How to Map FHIR Resources to Dew Nodes

The sanitizer owns this mapping. Dew never sees FHIR resources directly. The sanitizer translates FHIR resource state into graph topology before anything reaches Dew. The identifiers are opaque strings — Dew treats them as arbitrary labels.

| FHIR Resource | Dew Representation |
|---|---|
| `Location` | Node id (e.g., `BED_042`, `WARD_3N`, `OR_SUITE_2`) |
| `Practitioner` | Node id (e.g., `STAFF_017`, `ATTENDING_094`) |
| `Schedule` | Presence or absence of connections; edge weight changes |
| `Slot` | Edge weight (`1.0` = available, `999` = unavailable, absent = blocked) |

The sanitizer configuration determines which FHIR resource maps to which node id. Dew accepts whatever strings it receives. The mapping never changes after setup unless the sanitizer configuration changes.

---

## Example Anonymized Graph Instructions

**After a chart-save event — bed assignment routing:**

```json
POST /route
{
  "intent": "route to nearest available bed, prefer direct ward connections, block beds under maintenance",
  "graph": {
    "ADM_POINT_7": {
      "connections": ["WARD_3N", "WARD_4S"]
    },
    "WARD_3N": {
      "connections": ["ADM_POINT_7", "BED_042", "BED_043", "BED_044"]
    },
    "BED_042": {
      "connections": ["WARD_3N"]
    },
    "BED_043": {
      "connections": ["WARD_3N"],
      "weights": { "WARD_3N": 999 }
    },
    "BED_044": {
      "connections": ["WARD_3N"]
    },
    "WARD_4S": {
      "connections": ["ADM_POINT_7", "BED_071"]
    },
    "BED_071": {
      "connections": ["WARD_4S"]
    }
  },
  "start": "ADM_POINT_7",
  "target": "BED_042",
  "caller": "epic_sanitizer"
}
```

`BED_043` carries a high edge weight — the sanitizer translated a maintenance flag on that Location resource into a penalty weight. Dew will route around it without knowing why.

**After a constraint update event — appointment slot availability changed:**

```json
POST /route
{
  "intent": "route to nearest available appointment slot, avoid scheduling conflicts",
  "graph": {
    "REF_SOURCE_881": {
      "connections": ["DEPT_CARDIO", "DEPT_ORTHO"]
    },
    "DEPT_CARDIO": {
      "connections": ["REF_SOURCE_881", "SLOT_C_1400", "SLOT_C_1500"]
    },
    "SLOT_C_1400": {
      "connections": ["DEPT_CARDIO"],
      "weights": { "DEPT_CARDIO": 999 }
    },
    "SLOT_C_1500": {
      "connections": ["DEPT_CARDIO"]
    },
    "DEPT_ORTHO": {
      "connections": ["REF_SOURCE_881", "SLOT_O_0900"]
    },
    "SLOT_O_0900": {
      "connections": ["DEPT_ORTHO"]
    }
  },
  "start": "REF_SOURCE_881",
  "target": "SLOT_C_1500",
  "caller": "constraint_updater"
}
```

`SLOT_C_1400` was previously weight `1.0`. The attending's schedule changed. The intranet endpoint detected the Slot resource update and posted an updated graph with `SLOT_C_1400` penalized. The next routing call received the new graph. No manual step.

---

## Hospital Staff Responsibility

Epic staff configure sanitized output within Epic. That is their entire responsibility.

They do not interact with Dew. They do not configure the intranet endpoint. They do not call `/synthesize`. They do not know Dew exists. Their workflow is unchanged.

---

## Which FHIR Resource Types Feed the Sanitizer and the Intranet Endpoint

| Resource | Contribution |
|---|---|
| `Location` | Node ids for beds, wards, rooms, and facilities; triggers a constraint update when status changes |
| `Schedule` | Determines which practitioner nodes are reachable and when; triggers a constraint update when availability changes |
| `Slot` | Edge weights representing appointment availability; triggers a constraint update when a slot opens or closes |
| `Practitioner` | Node ids for attending physicians, nurses, and specialists; referenced in Schedule resources |

---

## The Boundary

The sanitizer is the boundary.

Everything above it — FHIR resources, patient records, clinical data, Epic itself — is the hospital's existing HIPAA scope. The hospital already operates and controls this layer under its existing compliance program.

Everything below the boundary is Dew: anonymous strings, edge weights, math, a path. No PHI crosses the boundary because the sanitizer does not forward it. Dew has no mechanism to receive it and no knowledge that it exists.
