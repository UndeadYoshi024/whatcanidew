# DEW — KIRO CONTEXT DOCUMENT
## Current as of Session 3

---

## WHAT DEW IS

Domain-agnostic graph routing. Shortest path through any connected system. User expresses intent in natural language once — that intent becomes weights, weights shape the terrain, Dijkstra finds the river.

**No LLM. No API call. No network.** Intent synthesis is a deterministic keyword parser. Pure signal extraction. Instant. Auditable. Zero cost per call.

**The primitive:** BFS for unweighted graphs. Dijkstra for weighted. Auto-selected. Domain doesn't matter.

---

## REPO

**Location:** `C:/Dev/dew`
**Package name:** `dew` (PyPI), `dewdrops` (npm)

---

## CURRENT DIRECTORY STATE

```
dew/
  health.py                    — validates required JSON data files, watches for changes
  startup_hook.py              — startup gate, calls validate_repoe, warns on failure
  logger.py                    — append-only activity log
  intent_weight_synthesizer.py — keyword parser: intent → ConstraintProfile, no LLM
  graph_weight_mapper.py       — applies ConstraintProfile to graph
  entry_point.py               — orchestrates full pipeline, one call
  tree_topology_heuristics.py  — COPY of pypi/ core (never edit this copy)
  dir_reorganizer.py           — deterministic aesthetic directory renamer
  index.html                   — dark-mode UI: load graph, run Dew, snapshot, reorganize
  start.bat                    — launches uvicorn server locally on port 8000
  docker/
    Dockerfile, server.py, health.py, startup_hook.py
  pypi/
    tree_topology_heuristics.py — NEVER TOUCH, NEVER MOVE
    logger.py, intent_weight_synthesizer.py, graph_weight_mapper.py, entry_point.py
    health.py, startup_hook.py, profile_store.py, obscura.py, repoe_adapter.py
    pyproject.toml
  npm/
    index.ts, tsconfig.json, package.json
  postgres/
    tree_topology_heuristics.sql, health.py, startup_hook.py
  tests/
    conftest.py, mock_scheduler.py, test_core.py, test_entry_point.py,
    test_hospital.py, test_logger.py, test_weight_mapper.py, test_api.py,
    test_obscura.py, test_repoe_adapter.py, test_dir_reorganizer.py, test_ripple.py
```

---

## INTENT SYNTHESIS — HOW IT ACTUALLY WERKS

`intent_weight_synthesizer.py` is a **deterministic keyword parser**. No LLM. No Anthropic. No API key required.

It tokenizes the intent string and matches against four signal sets:

```python
_TIME_SIGNALS        = {"fast", "urgent", "quick", "asap", "deadline"}
_COST_SIGNALS        = {"cheap", "budget", "cost", "affordable", "save"}
_RELIABILITY_SIGNALS = {"safe", "reliable", "consistent", "stable", "trusted"}
_RISK_SIGNALS        = {"risky", "uncertain", "dangerous", "unpredictable"}
```

First match wins. Returns a preset weight distribution. Also parses inline node constraints:
- `avoid <node>` → constraints["avoid"]
- `prefer <node>` / `use <node>` → constraints["prefer"]
- `never <node>` / `not <node>` / `block <node>` → constraints["hard_block"]

The profile is written to the activity log immediately. Cached in `_profile_cache`. Persisted to `profiles.json` via `ProfileStore`. Same intent string never re-synthesizes.

---

## OPEN ITEMS

### 1. Import fix — startup_hook.py (ALL COPIES)
`docker/startup_hook.py`, `pypi/startup_hook.py`, and `postgres/startup_hook.py` all import
`from tools.health import validate_repoe` — that's the ChaosOrbBot path. They will crash on import.
Only the root-level `startup_hook.py` has the correct `from health import validate_repoe`.
Fix: update all three distro copies to match root.

### 2. health.py — wrong files checked (ALL COPIES)
All four copies of `health.py` (root, docker, pypi, postgres) check for:
  `games/poe1/bot_data/mods_jewel.json`
  `games/poe1/bot_data/mods_gear.json`
Those are ChaosOrbBot files. They don't exist here. Every health check fails.
Fix: decide what files Dew actually needs to validate at startup, update `_REQUIRED_FILES`.

### 3. Dead `api_key` / `DEW_API_KEY` references
The LLM was removed. These are orphaned:
- `start.bat` sets `DEW_API_KEY=none` — unnecessary
- `test_api.py` sets `os.environ.setdefault("DEW_API_KEY", ...)` — unnecessary
- `test_entry_point.py` and `test_hospital.py` pass `api_key=DUMMY_KEY` to `route()` — will TypeError
- `docker/Dockerfile` installs `anthropic` — dead weight
Fix: remove all of the above.

### 4. `entry_point.py` signature mismatch
Root-level `route()` takes `(user_intent, graph, start, target, log_path)`.
Tests pass `api_key=DUMMY_KEY` and `log_path` as positional — will TypeError.
Fix: update tests to match current signature, or add `**kwargs` to swallow legacy params.

### 5. `ripple.py` missing
`tests/test_ripple.py` imports from `ripple` but `pypi/ripple.py` does not exist.
All ripple tests fail with `ModuleNotFoundError`.
Fix: build `ripple.py` or delete `test_ripple.py`.

### 6. `dew-export` spec — Tasks 2–10 open
`profile_store.py` exists in `pypi/` but has not been promoted to root or integrated into
`entry_point.py` or `docker/server.py`. The spec is mid-flight.
Fix: execute remaining tasks per `.kiro/specs/dew-export/tasks.md`.

### 7. Dockerfile is stale
Does not copy `repoe_adapter.py`, `obscura.py`, `profile_store.py`, or `dir_reorganizer.py`,
all of which `docker/server.py` now imports.
Fix: add missing COPY lines.

### 8. `__init__.py` missing
`from dew import TreeTopologyHeuristics` won't work until this exists.
Waiting on: PyPI org "dew" approval + `whatcanidew.com` domain.

### 9. PostgreSQL distro incomplete
`postgres/tree_topology_heuristics.sql` exists. BFS only — no Dijkstra, no weights.
Needs: packaging, install instructions, test against PostgreSQL 12+.

### 10. Snowflake / Databricks UDFs
Parked until environments available.

### 11. Salesforce Connector
Scoped. Needs specialist or middleware access.

### 12. SAP Connector
Scoped. Needs SAP specialist.

### 13. `whatcanidew.com`
Buying Friday (payday). Unlocks: App Orchard application, `hello@whatcanidew.com` going live, `__init__.py` build.

### 14. Epic App Orchard application
Needs `whatcanidew.com` live first. Docs complete: `EPIC.md`, `FHIR.md`, `HIPAA.md`.

### 15. Cloudflare deployment update
New modules need to be pushed to the Cloudflare Worker at `tiny-glitter-23ae.kleinberryblake.workers.dev`.

### 16. npm — TypeScript equivalents of health.py and startup_hook.py
`npm/` is TypeScript. These need TS equivalents written and added.

### 17. Omnibus module
Separate product. Takes Dew output, translates for legal/paralegal/document review.
Not a Dew core module. Timeline TBD.

---

## CORE RULES FOR ANY AGENT WORKING HERE

- `pypi/tree_topology_heuristics.py` — NEVER TOUCH, NEVER MOVE. The class name stays `TreeTopologyHeuristics`. The import stays `from tree_topology_heuristics import TreeTopologyHeuristics, TreeNode`.
- Root-level files are source of truth. Distro copies are copies — never edit them directly.
- Never edit distro files directly — always promote from root.
- The package name is `dew`. The module name is `tree_topology_heuristics`. Python doesn't care that they differ.
- There is no LLM call anywhere in this codebase. Do not add one. Do not reference `api_key` or `anthropic` in new code.
- Brand voice: "dew" replaces "do" when Dew is the subject. Never forced. Automated processes "werk." Human labor "works."

---

## CONTACT

hello@whatcanidew.com (live Friday)
