Dew
Intent-driven graph routing for any connected system.
> "What do you need it to dew?"
---
What it dews
Dew is an overlay, not a database. You bring the data. Dew brings the topology.
Point it at any flat data structure with nodes and relationships — a skill tree, a supply chain, a hospital floor plan, a freight network — and Dew superimposes a weighted graph on top of it. Express your intent in plain language. Dew synthesizes it into constraints, shapes the terrain, and finds the path.
Your data stays your data. Dew is the lens.
---
The two layers
Dew always works on two layers:
Your flat data — the source of truth. JSON, a database, a game export, a warehouse manifest, whatever you have.
The graph — what Dew builds from it. Nodes, edges, weights shaped by your intent.
Dew reads both. The flat data is never discarded — it's the context the graph lives on top of. When you apply constraints or query paths, you're querying the overlay, not replacing the source.
---
Install
Pick your stack.
Python
```bash
pip install tree-topology-heuristics
```
JavaScript / TypeScript
```bash
npm install dewdrops
```
Docker (any language)
```bash
docker pull dew/api
docker run -p 8000:8000 dew/api
```
PostgreSQL
```sql
CREATE EXTENSION dew;
```
---
Quick start
Python
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
TypeScript
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
REST API
```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"start": "a", "target": "d", "user_intent": "fastest path"}'
```
---
Intent-driven routing
Dew doesn't just find shortest paths — it finds the right path for what you actually need.
```python
from entry_point import route

result = route(
    user_intent="get there fast, avoid construction",
    graph=graph,
    start="warehouse",
    target="customer",
    api_key="your-key"
)
```
Dew synthesizes your intent into weights and constraints, shapes the graph terrain, then routes. The same graph returns a different path depending on who's asking and what they need.
Every decision is logged. You can always see exactly why the terrain was shaped the way it was, and exactly what path the water took.
---
Distros
Distro	Target	Install
PyPI	Python developers, data scientists	`pip install tree-topology-heuristics`
npm	JavaScript / TypeScript, web apps	`npm install dewdrops`
Docker	Any language, universal fallback	`docker pull dew/api`
PostgreSQL	Any company running PostgreSQL 12+	`CREATE EXTENSION dew`
Snowflake	Data teams on Snowflake	Coming soon
Databricks	Data engineering on Databricks	Coming soon
Salesforce	Enterprise Salesforce orgs	Coming soon
SAP	Enterprise SAP installations	Coming soon
Startup bundle
PyPI + npm + Docker. Three commands, runs anywhere. No enterprise contracts needed.
Enterprise bundle
PostgreSQL + Snowflake + Databricks + REST API + support contract. For mid-to-large orgs with existing analytics infrastructure.
---
What can it dew?
Freight routing
Patient triage and bed assignment
Warehouse picking paths
Skill tree navigation
Invoice approval chains
Supply chain optimization
Anything with nodes and edges
> [whatcanidew.com](https://whatcanidew.com)
---
Zero dependencies
The core math — BFS and Dijkstra — has zero runtime dependencies in every distro. It runs anywhere its host environment runs.
---
License
TBD
