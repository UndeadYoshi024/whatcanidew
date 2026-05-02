# DEW — FLIGHT HANDOFF DOCUMENT
## Context Export — May 2026 | Session 3
### For: Any agent, any session, any wallet

---

## THE ONE SENTENCE

> "It superimposes non-Euclidean space on a Euclidean substrate."

Technical buyer: stops the meeting.
Business buyer: asks what it means.
Either way you have the room.

---

## WHAT DEW IS

Dew is a domain-agnostic graph routing product. It finds the shortest path through any connected system. The user expresses intent in natural language once. That intent becomes weights. The weights shape the terrain. Dijkstra finds the river.

Your data is flat. Your problems aren't. Dew finds the real shape underneath and hands you back something flat.

**The rain analogy (for non-technical buyers):**
Your data is paper. Paper is 2D. Dew superimposes a NOT flat space onto that surface and makes it rain. The rain fills the valleys. It makes a river. That river connects point A to point B the fastest. How it makes the hills is by weighting abstract data — via keyword extraction at setup, or via natural statistical weight in existing data. All customizable.

**The tagline:** Signal from noise. Every time.
**The brand:** Dew is a verb. "What dews this app dew?" "It dews freight." "What do you need it to dew?"

---

## WHAT DEW DEWS

- Freight and logistics
- Medical triage and scheduling
- Warehouse control and pick path optimization
- EDI workflow routing
- Invoice and approval hierarchies
- Passive skill trees (original domain — POE)
- Paralegal document review (via Omnibus — see below)
- Anything with nodes and edges

**The primitive:** BFS for unweighted graphs. Dijkstra for weighted. Auto-selected. Domain doesn't matter.

---

## THE PITCH BY BUYER TYPE

**Technical:** "It superimposes non-Euclidean space on a Euclidean substrate."
**Business:** "What do you need it to dew?"
**Nurse/clinical staff:** Nothing. She never knows it exists. She just notices things got easier.
**CFO:** One less bank call. One less reconciliation headache.
**Compliance officer:** Append-only audit log. Every decision. Human readable. No PHI.

**The metric:** Did the nurse cry? Not because of software — because someone finally built something that just lets her do her job.

---

## THE ARCHITECTURE

### Runtime Flow (Healthcare example)
1. Nurse charts. Hits save. Done — workflow unchanged.
2. Pre-configured sanitization layer intercepts chart event, strips PHI, posts anonymized graph to Dew.
3. Dew applies cached constraint profile. Runs Dijkstra. Returns path.
4. Bed gets assigned. Appointment gets scheduled. Log entry written.
5. Doctor updates availability → intranet endpoint detects change → posts updated graph to Dew.
6. Nobody reconfigured anything. Nobody opened a new tool. The math just ran.

### Intent Synthesis — How It Actually Werks
There is no LLM. There never needs to be.

IT describes the routing problem in plain language. Dew's keyword parser reads the intent string, matches against signal sets (time, cost, reliability, risk), and returns a `ConstraintProfile` with preset weight distributions. Inline node constraints (`avoid <node>`, `prefer <node>`, `block <node>`) are parsed directly from the string.

The profile is written to the append-only log immediately. Cached in memory. Persisted to `profiles.json`. The same intent string never re-synthesizes — not because the LLM is cached, but because the math is deterministic and the result is stored.

**Why this is better than an LLM:**
- Zero cost per call
- Zero latency
- Zero hallucination risk
- Fully auditable — you can read exactly what signal was matched and why
- Works offline, air-gapped, in a container with no outbound network

### Why It's Not a Black Box
- Every profile is written to the append-only log the moment it's synthesized.
- Every routing decision logged as: timestamp, start node, target node, path sequence, distance, caller.
- Humans read it. No software required. Compliance officers and auditors can read it directly.
- You can show exactly what the intent string said, what weights that produced, what path the math found.

### Security Story
- Intent synthesis never touches your data. It reads your words, returns a weights map, and gets out.
- Your graph stays in your system. Dijkstra runs in your system.
- You can't prompt inject a pathfinding algorithm.
- No outbound network calls during routing. Ever.

---

## THE PIPELINE (How We Build)

Four layers:

**Layer 1 — Me (Claude webapp):**
Stage map, intent, orchestration, evaluation. I hold the full context. I write orchestrator prompts. I evaluate all outputs before anything promotes.

**Layer 2 — Claude Code (VS Code extension):**
Reads the full Dew directory. Retools Layer 1 prompts against actual codebase. Quality gate. Corrects import paths, conventions, inconsistencies. Returns a corrected prompt for Layer 3.

**Layer 3 — Fresh baby agents:**
Single task. Single file. No ambient context. Receive only the retooled prompt from Layer 2. Write code. Return output.

**Layer 4 — Amazon Q:**
Top-level auditor. Enormous context window. Reviews final outputs. Brand voice sweep. Consistency check. Free wallet.

**The rule:** Nothing touches the Dew dir until it clears my evaluation. Workers can read files they're instructed to read. They can only append to the handoff through me. They never draw from this handoff directly.

---

## THE REPO

**Location:** `C:/dev/dew`
**Repo:** `/whatcanidew`

### Directory Structure
```
dew/
  logger.py                    — append-only activity log, shared across all distros
  intent_weight_synthesizer.py — keyword parser: intent → ConstraintProfile, no LLM
  graph_weight_mapper.py       — applies ConstraintProfile to graph before routing
  entry_point.py               — orchestrates full pipeline, one call
  tree_topology_heuristics.py  — COPY of pypi/ core for local imports (never edit)
  dir_reorganizer.py           — deterministic aesthetic directory renamer
  index.html                   — dark-mode UI: load graph, run Dew, snapshot, reorganize
  start.bat                    — launches uvicorn server locally on port 8000
  QUICKSTART.md                — user-facing quick start
  README.md                    — distro manifest
  EPIC.md                      — Epic App Orchard one-pager
  FHIR.md                      — FHIR integration guide for IT
  HIPAA.md                     — HIPAA architecture statement for compliance/procurement
  DEW_BRAND_VOICE.md           — brand voice, internal culture, language rules
  docker/
    Dockerfile                 — copies all modules from repo root
    server.py                  — FastAPI REST API, all endpoints
  pypi/
    tree_topology_heuristics.py — core math (BFS + Dijkstra), NEVER TOUCH, NEVER MOVE
    profile_store.py           — atomic disk persistence for ConstraintProfile objects
    obscura.py                 — profile cache serialization: snapshot, rollback, migration
    repoe_adapter.py           — converts flat JSON to TreeNode graph
    pyproject.toml             — pypi package config
  npm/
    index.ts                   — TS wrapper
    package.json               — npm package config
  postgres/
    tree_topology_heuristics.sql — PostgreSQL PL/Python3u extension
  tests/
    conftest.py                — shared fixtures: graphs, profiles, log paths
    mock_scheduler.py          — fake Epic sanitizer, anonymized graph events
    test_core.py               — TreeTopologyHeuristics unit tests
    test_entry_point.py        — pipeline + cache tests
    test_hospital.py           — full healthcare routing integration tests
    test_logger.py             — ActivityLog tests
    test_weight_mapper.py      — graph_weight_mapper tests
    test_api.py                — FastAPI endpoint tests
    test_obscura.py            — obscura serialization tests
    test_repoe_adapter.py      — repoe_adapter tests
    test_dir_reorganizer.py    — dir_reorganizer tests
    test_ripple.py             — ripple tests (ripple.py not yet built)
```

### The Core Math File
`tree_topology_heuristics.py` — NEVER TOUCH. The class name stays `TreeTopologyHeuristics`. The import stays `from tree_topology_heuristics import TreeTopologyHeuristics, TreeNode`. The package name is `dew` but the module name is `tree_topology_heuristics`. Python doesn't care that they differ.

---

## THE MODULES

### tree_topology_heuristics.py
Core math. BFS (unweighted) or Dijkstra (weighted), auto-selected.
- `TreeNode(id, connections, weights)` — weights dict = neighbor_id → edge cost
- `PathResult(distance, path)` — distance=-1 if unreachable
- `NearestResult(target_id, distance, path)`
- `TreeTopologyHeuristics.find_path(graph, start, target) → PathResult`
- `TreeTopologyHeuristics.find_nearest(graph, start, candidates) → NearestResult`
- `TreeTopologyHeuristics.calculate_graph_distance(graph, start, target) → float`

### logger.py
Append-only activity log. Humans read it.
- `ActivityLog(filepath)` — creates log file if not exists
- `.write(start, target, distance, path, caller, note)` — one line per routing decision
- `.write_nearest(start, candidates, nearest, distance, path, caller, note)`
- `.rotate()` — archives current log, starts fresh. Manual only, never automated.

### intent_weight_synthesizer.py
Keyword parser: intent string → ConstraintProfile. No LLM. No API call. No network.
- `IntentWeightSynthesizer(log)`
- `.synthesize(user_intent, caller) → ConstraintProfile`
- `ConstraintProfile(profile_name, intent_summary, weights, constraints, notes, raw_intent)`
- weights keys: time, cost, risk, reliability, distance — sum to 1.0
- constraints keys: avoid, prefer, hard_block — each a list of node id strings
- Writes profile to log immediately. Profile is permanent.

### graph_weight_mapper.py
Applies ConstraintProfile to graph. Pure transformation, no side effects.
- `apply_weights(graph, profile, penalty_factor=10.0, reward_factor=0.5) → Dict[str, TreeNode]`
- Deep copies input graph — never mutates original
- Order: hard_block removal → composite edge cost → avoid penalty → prefer reward
- hard_block nodes removed entirely — Dijkstra never sees them

### entry_point.py
Orchestrates full pipeline. One call.
- `route(user_intent, graph, start, target, log_path) → PathResult`
- Module-level `_profile_cache` — same intent string never re-synthesizes
- Pipeline: check cache → synthesize (if miss) → apply_weights → find_path → log.write → return

### docker/server.py
FastAPI REST API.
- `POST /path` — full route with path sequence
- `POST /distance` — hop count only
- `POST /nearest` — nearest reachable from candidate set
- `GET /health` — liveness check
- `POST /synthesize` — intent → ConstraintProfile
- `POST /route` — full pipeline in one call
- `POST /load` — load graph from file or directory path
- `POST /route-stored` — route on the stored graph
- `POST /path-stored` — path on the stored graph
- `POST /run` — cluster analysis on stored graph
- `POST /snapshot` — write `.dew` snapshot to logs/
- `GET /log` — last 20 lines of activity log
- `POST /reorganize` — aesthetic directory rename via dir_reorganizer

### profile_store.py (pypi/)
Atomic disk persistence for ConstraintProfile objects.
- `ProfileStore(profiles_path=None)` — path resolution: arg → DEW_PROFILES_PATH → DEW_LOG_PATH dir → logs/profiles.json
- `.save(profile)` — upsert by profile_name, atomic write
- `.load_all() → List[ConstraintProfile]` — never raises, returns [] on missing/malformed

### obscura.py (pypi/)
Profile cache serialization utilities.
- `export_profiles(cache)` / `import_profiles(data)` — roundtrip
- `snapshot(cache, path)` — writes `.dew` file
- `rollback(cache)` — deep copy
- `export_migration(cache)` / `import_migration(data)` — migration bundle
- `edit_profile(cache, key, updated, reason)` — tombstones old entry, inserts new

### repoe_adapter.py (pypi/)
Converts flat JSON to TreeNode graph.
- `build_graph(data) → Dict[str, TreeNode]` — handles string, list, and mixed values
- `find_disconnected(graph) → List[List[str]]` — returns components sorted by size
- `merge(base, extra) → Dict[str, TreeNode]` — non-mutating graph merge
- `load(path) → Dict[str, TreeNode]` — walks directory, handles dew.config.json, interactive merge

### dir_reorganizer.py
Deterministic aesthetic directory renamer.
- `reorganize(source) → str` — copies to `<source>_dew/` with normalized names
- Rules: lowercase, spaces/hyphens → underscores, collapse runs, strip leading/trailing

---

## INFRASTRUCTURE

| Thing | Status |
|---|---|
| `pip install dew` | PyPI org "dew" — pending approval |
| `npm install dewdrops` | Live — `dew` was taken on npm |
| `orbbot.xyz` | Owned, Namecheap DNS, Cloudflare Workers |
| `whatcanidew.com` | Not yet — buying Friday (payday) |
| `hello@whatcanidew.com` | In all docs, ready when domain is live |
| Cloudflare Worker | Live at tiny-glitter-23ae.kleinberryblake.workers.dev |
| `__init__.py` | NEEDED — so `from dew import` works after PyPI clears |

---

## KNOWN BROKEN THINGS (as of Session 3)

| Issue | Location | Fix |
|---|---|---|
| Wrong import path | `docker/startup_hook.py`, `pypi/startup_hook.py`, `postgres/startup_hook.py` | Change `from tools.health` to `from health` |
| Wrong files checked | All four `health.py` copies | Update `_REQUIRED_FILES` to Dew's actual files |
| Dead `api_key` param | `test_entry_point.py`, `test_hospital.py` | Remove `api_key=DUMMY_KEY` from `route()` calls |
| Dead `DEW_API_KEY` env | `start.bat`, `test_api.py` | Remove |
| Dead `anthropic` install | `docker/Dockerfile` | Remove from pip install line |
| Missing COPY lines | `docker/Dockerfile` | Add `repoe_adapter.py`, `obscura.py`, `profile_store.py`, `dir_reorganizer.py` |
| `ripple.py` missing | `pypi/` | Build it or delete `test_ripple.py` |
| `__init__.py` missing | root | Build after PyPI + domain clear |
| dew-export Tasks 2–10 | `.kiro/specs/dew-export/tasks.md` | Execute remaining tasks |

---

## WHAT'S NOT BUILT YET

- **`__init__.py`** — re-exports from `tree_topology_heuristics` so `from dew import TreeTopologyHeuristics` works.
- **`ripple.py`** — codebase call graph analysis and refactor propagation tool. Tests exist, module doesn't.
- **Omnibus module** — Dew output dressed for legal/paralegal/document review. Different product. Not a Dew core module.
- **Cerner/Meditech distros** — same structure as Epic, different resource mappings.
- **Snowflake/Databricks UDFs** — need those environments to test.
- **App Orchard application** — needs `whatcanidew.com` live first.

---

## DISTRO ROADMAP

| Distro | Status |
|---|---|
| PyPI | COMPLETE |
| npm (dewdrops) | COMPLETE |
| Docker / REST API | COMPLETE |
| PostgreSQL | IN PROGRESS |
| Snowflake UDF | NEEDS SNOWFLAKE ENV |
| Databricks UDF | NEEDS DATABRICKS ENV |
| Salesforce Connector | SCOPED — needs specialist |
| SAP Connector | SCOPED — needs specialist |
| Epic (healthcare) | DOCS COMPLETE — App Orchard pending |
| Cerner | FUTURE |
| Meditech | FUTURE |

**Bundles:**
- Startup: pip + npm + Docker
- Enterprise: PostgreSQL + Snowflake + Databricks + REST API + support contract

---

## RELATED PRODUCTS

**Omnibus:** Separate product. Not a Dew core module. Takes Dew output and translates it into whatever the enterprise receiver needs — legal docs, paralegal flagged review, compliance reports. Same math, different costume. Legal/paralegal domain. Not healthcare. Not HIPAA adjacent.

**ChaosOrbBot:** The source project. Lives in PleaseWork/. Has its own handoff doc. The passive skill tree pathfinding was the original domain that proved the primitive works. Dew is the productized version of that primitive.

---

## OWNER

Blake. Bipolar, 36, on disability. Built something that dews hospitals, warehouses, freight networks, and skill trees with the same math. The code waits. It's not going anywhere.

> "I haven't had the sales call and anything less than 500k will make me yawn and hang up."
