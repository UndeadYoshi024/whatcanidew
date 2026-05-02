# Dew for Epic App Orchard
<!-- Template: substitute marketplace name, orchard/bushel/field terminology as needed for Cerner, Apple Health, etc. -->
## What Dew Dews

A nurse charts a patient. She hits save. That is the last thing she dews. A pre-configured sanitization layer running inside the hospital network intercepts the chart event, strips all protected health information, and posts an anonymized routing request to Dew. Dew runs the math. A bed gets assigned. An appointment gets scheduled. Meanwhile, a doctor changes her availability in Epic. The graph updates automatically — a hospital intranet endpoint that IT configured once is watching for exactly that event, and it sends an updated graph to Dew before the next routing call arrives. Nobody reconfigured anything. Nobody opened a new tool. Nobody filed a ticket. The math just ran.

## Why Epic Customers Want It

Hospital operations route constantly — beds, staff, rooms, appointment slots, triage priority, transfer decisions. Every one of these is a shortest-path problem on a constraint graph. When the constraints change, the routes need to update. When they do not, resources sit idle, queues grow, and staff compensate manually.

Dew dews this automatically. Bed assignment. Staff allocation. Appointment scheduling. Triage routing. The right resource, the fastest path, every time something changes — without anyone managing it.

## How It Plugs In

Epic staff configure sanitized output within Epic. That is the full extent of their involvement. They do not interact with Dew. They do not need to know Dew exists.

IT deploys the Dew Docker container. IT configures Epic's sanitized output to post anonymized graph instructions to Dew on each chart-save event. IT configures a hospital intranet endpoint to watch for constraint change events — doctor availability, room status, bed capacity — and send updated graph instructions to Dew automatically. IT runs `/synthesize` once per routing use case, describing the problem in plain language. The profile is written, cached, and permanent. After that: nothing. Dew runs on every chart-save and every constraint change, indefinitely, without further configuration.

## What the IT Person Actually Dews

One time:

1. Deploy the container: `docker run -p 8000:8000 -v $(pwd)/logs:/app/logs dew`
2. Configure Epic's sanitized output to `POST /route` on each chart-save event.
3. Configure the hospital intranet endpoint to watch Schedule, Slot, Location, and Practitioner resources and `POST` updated graph instructions to Dew when constraints change.
4. Call `POST /synthesize` once per routing use case with a plain-language description of the routing problem — bed assignment, appointment scheduling, triage priority, or anything else. Dew's keyword parser shapes the terrain. Dijkstra finds the path.

After that: nothing. The system stays current because the endpoint keeps it current. Dijkstra runs on every chart-save, forever.

## HIPAA Posture

Dew never receives PHI.

The hospital's existing sanitization layer strips all protected information before anything reaches Dew. Dew receives only anonymous graph structure: opaque node identifiers, connections, and optional weights. The API has no fields for names, dates of birth, diagnoses, insurance information, medical record numbers, or any of the 18 HIPAA identifiers. They cannot enter Dew because the sanitizer does not forward them.

The activity log is append-only plain text. Every runtime entry contains: timestamp, anonymous start node id, anonymous target node id, path as a sequence of anonymous node ids, distance, and caller name. No PHI in any entry, ever. A Business Associate Agreement is recommended. Contact hello@whatcanidew.com.

## The Metric

Did the nurses' eyes get dew-y?

Not because of software. Because someone finally built something that just lets them do their jobs.

---

**Contact:** hello@whatcanidew.com
