# Dew — HIPAA Architecture Statement

This document describes Dew's data posture for compliance officers and procurement. It is a technical architecture statement, not a legal opinion. Engage qualified counsel for regulatory determinations specific to your organization.

---

## What Dew Receives

Dew receives anonymous graph instructions produced by the hospital's pre-configured sanitization layer. Each instruction contains:

- **Node identifiers** — opaque strings (e.g., `BED_042`, `WARD_3N`, `SLOT_C_1500`). These are arbitrary labels chosen by the sanitizer configuration. They carry no patient context.
- **Connections** — adjacency lists defining which nodes are reachable from which.
- **Edge weights** — floating-point numbers representing routing cost. An unavailable resource is a high weight. A blocked resource is absent from the graph.
- **Routing parameters** — a start node id and a target node id.

This is the complete input surface of Dew at runtime. There are no other fields. There is no free-form text input at runtime. There is no patient context.

---

## What Dew Never Receives

Dew's API has no fields for:

- Names
- Dates of birth
- Geographic data smaller than state
- Telephone numbers
- Fax numbers
- Email addresses
- Social security numbers
- Medical record numbers
- Health plan beneficiary numbers
- Account numbers
- Certificate or license numbers
- Vehicle identifiers
- Device identifiers and serial numbers
- Web URLs
- IP addresses
- Biometric identifiers
- Full-face photographs
- Diagnoses, conditions, or clinical findings
- Insurance information

These are the 18 HIPAA identifiers. None of them can enter Dew because the sanitizer does not forward them and the API provides no mechanism to receive them.

---

## Where PHI Lives

PHI lives in the hospital's existing systems — Epic, the EHR database, the FHIR server. The sanitization layer is the boundary between those systems and Dew. PHI never crosses it.

The hospital already operates and controls the sanitization layer and the Epic configuration under its existing HIPAA compliance program. Dew is downstream of a boundary the hospital already owns. The hospital's compliance posture for Dew is limited to the configuration of sanitized output within Epic — work performed entirely within systems already in scope.

---

## Intent Synthesis

The IT professional calls `POST /synthesize` once per routing use case with a plain-language description of the routing problem. Dew's keyword parser reads the intent and shapes terrain: what to prefer, what to penalize, what to block entirely. The resulting constraint profile is written to the activity log and cached. The same intent string never re-synthesizes — the profile is stored and reused on every subsequent routing call.

Intent synthesis runs entirely on the host. No external service is called. No data leaves the container.

---

## The Audit Log

The activity log is an append-only plain text file stored on the host running the Dew container. It is never modified — only extended. It cannot be edited through the API. Log rotation is performed manually by the IT operator when size requires it; archived files are preserved.

**Runtime entries contain:**
- Timestamp (UTC)
- Anonymous start node id
- Anonymous target node id
- Path as an ordered sequence of anonymous node ids
- Routing distance
- Caller name (a label provided by the sanitizer or intranet endpoint, configured by IT)

**Setup entries contain:**
- Routing profile name
- Intent summary (the IT professional's plain-language description)
- Constraint weights and classifications (prefer, avoid, hard block)

No entry in either category contains PHI. The log is human-readable without any software. Compliance officers and auditors can read it directly.

---

## Business Associate Agreement

A BAA is recommended.

Dew operates as an adjacent system in a healthcare workflow. It receives no PHI. It processes no clinical data. It is downstream of a sanitization boundary the hospital already controls. Nevertheless, standard procurement posture for systems operating adjacent to healthcare workflows — even systems that do not process PHI — is to establish a Business Associate Agreement as a matter of institutional practice.

Contact hello@whatcanidew.com to initiate a BAA.

---

## The Sanitization Responsibility

The sanitization responsibility belongs entirely to the hospital's existing sanitization layer and the Epic staff who configure sanitized output within Epic.

Dew inherits a clean input. It has no visibility into the sanitizer's implementation, configuration, or data handling. It has no mechanism to inspect, reject, or validate whether the inputs it receives were correctly sanitized — it accepts the graph it is sent. The hospital's compliance program is responsible for ensuring the sanitization layer performs correctly before data reaches Dew.

This is the correct division of responsibility. The sanitizer is inside the hospital's perimeter. Dew is outside it. The hospital controls what crosses that line.
