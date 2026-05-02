# Dew
Intent-driven graph routing for any connected system.

> "What do you need it to dew?"

---

## What it dews

Dew is an overlay, not a database. You bring the data. Dew brings the topology.

Point it at any flat data structure with nodes and relationships — a skill tree, a supply chain, a hospital floor plan, a freight network — and Dew superimposes a weighted graph on top of it. Express your intent in plain language. Dew synthesizes it into constraints, shapes the terrain, and finds the path.

Your data stays your data. Dew is the lens.

---

## The modules

**`tree_topology_heuristics.py`**
The core math. BFS for unweighted graphs. Dijkstra for weighted. Auto-selected. Zero dependencies. Runs anywhere its host environment runs.

**`intent_weight_synthesizer.py`**
Converts natural language intent into a `ConstraintProfile` using a deterministic keyword parser. No API call. No network. No LLM. Pure signal extraction — your words become weights, the weights shape the terrain, Dijkstra finds the river.

**`graph_weight_mapper.py`**
Applies a `ConstraintProfile` to a graph. Penalizes avoid nodes. Rewards prefer nodes. Removes hard_block nodes entirely. Returns a weighted graph ready for routing.

**`entry_point.py`**
Orchestrates the full Dew pipeline. Intent → profile → weighted graph → path → log. One call. Same intent string never re-synthesizes — the profile is cached in memory and persisted to disk.

---

## The two layers

Dew always works on two layers:

1. **Your flat data** — the source of truth. JSON, a database, a game export, a warehouse manifest, whatever you have.
2. **The graph** — what Dew builds from it. Nodes, edges, weights shaped by your intent.

Dew reads both. The flat data is never discarded — it's the context the graph lives on top of. When you apply constraints or query paths, you're querying the overlay, not replacing the source.

---

## Install

Pick your stack.

**Python**
```bash
pip install dew
```

**JavaScript / TypeScript**
```bash
npm install dewdrops
```

**Docker (any language)**
```bash
docker build -t dew -f docker/Dockerfile .
docker run -p 8000:8000 -v $(pwd)/logs:/app/logs dew
```

**PostgreSQL**
```sql
CREATE EXTENSION dew;
```

---

## Quick start

**Python**
```python
from tree_topology_heuristics import TreeTopologyHeuristics, TreeNode

graph = {
    'a': TreeNode('a', connections=['b', 'c'], weights={'b': 1, 'c': 4}),
    'b': TreeNode('b', connections=['d'], weights={'d': 2}),
    'c': TreeNode('c', connections=['d'], weights={'d': 1}),
    'd': TreeNode('d', connections=[], weights={}),
}

result = TreeTopologyHeuristics.find_path(graph, 'a', 'd')
print(result.path)      # ['a', 'c', 'd']
print(result.distance)  # 5
```

**TypeScript**
```typescript
import { TreeTopologyHeuristics, TreeNode } from 'dewdrops'

const graph: Record<string, TreeNode> = {
  a: { id: 'a', connections: ['b', 'c'], weights: { b: 1, c: 4 } },
  b: { id: 'b', connections: ['d'], weights: { d: 2 } },
  c: { id: 'c', connections: ['d'], weights: { d: 1 } },
  d: { id: 'd', connections: [], weights: {} },
}

const result = TreeTopologyHeuristics.findPath(graph, 'a', 'd')
console.log(result.path)     // ['a', 'c', 'd']
console.log(result.distance) // 5
```

**REST API**
```bash
curl -X POST http://localhost:8000/path \
  -H "Content-Type: application/json" \
  -d '{
    "graph": {
      "a": {"connections": ["b", "c"], "weights": {"b": 1, "c": 4}},
      "b": {"connections": ["d"], "weights": {"d": 2}},
      "c": {"connections": ["d"], "weights": {"d": 1}},
      "d": {"connections": [], "weights": {}}
    },
    "start": "a",
    "target": "d"
  }'
```

---

## Intent-driven routing

Dew doesn't just find shortest paths — it finds the right path for what you actually need.

```python
from entry_point import route

result = route(
    user_intent="get there fast, avoid construction",
    graph=graph,
    start="warehouse",
    target="customer"
)
```

Dew parses your intent into weights and constraints, shapes the graph terrain, then routes. The same graph returns a different path depending on who's asking and what they need.

**Intent keywords:**
- Time-dominant: `fast`, `urgent`, `quick`, `asap`, `deadline`
- Cost-dominant: `cheap`, `budget`, `cost`, `affordable`, `save`
- Reliability-dominant: `safe`, `reliable`, `consistent`, `stable`, `trusted`
- Risk-averse: `risky`, `uncertain`, `dangerous`, `unpredictable`
- Node constraints: `avoid <node>`, `prefer <node>`, `block <node>`, `never <node>`

Every profile is written to the activity log the moment it's synthesized. Permanent. Auditable. Human-readable.

---

## The activity log

Every routing decision is written to `logs/routing_decisions.log`.

```
[2026-05-01 21:47:38 UTC] | FROM: warehouse | TO: customer | DISTANCE: 2 | PATH: warehouse -> hub -> customer | CALLER: entry_point
```

This file only grows. It is never modified. It is never deleted. Compliance officers, auditors, and operations managers can read it without any software.

---

## Distros

| Distro | Target | Install |
|---|---|---|
| PyPI | Python developers, data scientists | `pip install dew` |
| npm | JavaScript / TypeScript, web apps | `npm install dewdrops` |
| Docker | Any language, universal fallback | `docker pull dew/api` |
| PostgreSQL | Any company running PostgreSQL 12+ | `CREATE EXTENSION dew` |
| Snowflake | Data teams on Snowflake | Coming soon |
| Databricks | Data engineering on Databricks | Coming soon |
| Salesforce | Enterprise Salesforce orgs | Coming soon |
| SAP | Enterprise SAP installations | Coming soon |

**Startup bundle:** PyPI + npm + Docker. Three commands, runs anywhere.

**Enterprise bundle:** PostgreSQL + Snowflake + Databricks + REST API + support contract.

---

## What can it dew?

- Freight routing
- Patient triage and bed assignment
- Warehouse picking paths
- Skill tree navigation
- Invoice approval chains
- Supply chain optimization
- Anything with nodes and edges

[whatcanidew.com](https://whatcanidew.com)

---

## Zero dependencies

The core math — BFS and Dijkstra — has zero runtime dependencies in every distro.

---

## License

TBD
