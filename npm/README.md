# dewdrops

Shortest path between any two nodes in any connected graph. BFS and Dijkstra. Zero dependencies.

```
npm install dewdrops
```

---

## What it dews

dewdrops is an overlay, not a database. You bring the data. dewdrops brings the topology.

Point it at any flat data structure with nodes and relationships — a skill tree, a supply chain, a hospital floor plan, a freight network — and dewdrops superimposes a weighted graph on top of it. Your data stays your data. dewdrops is the lens.

---

## Usage

```typescript
import { TreeTopologyHeuristics, TreeNode } from 'dewdrops'

const graph: Record<string, TreeNode> = {
  a: { id: 'a', connections: ['b', 'c'], weights: { b: 1, c: 4 } },
  b: { id: 'b', connections: ['d'], weights: { d: 2 } },
  c: { id: 'c', connections: ['d'], weights: { d: 1 } },
  d: { id: 'd', connections: [], weights: {} },
}

// Weighted shortest path — Dijkstra auto-selected
const result = TreeTopologyHeuristics.findPath(graph, 'a', 'd')
console.log(result.path)     // ['a', 'c', 'd']
console.log(result.distance) // 5

// Nearest node from a candidate set
const nearest = TreeTopologyHeuristics.findNearest(graph, 'a', ['c', 'd'])
console.log(nearest.target_id) // 'c'
console.log(nearest.distance)  // 4

// Distance only
const dist = TreeTopologyHeuristics.calculateGraphDistance(graph, 'a', 'd')
console.log(dist) // 5
```

---

## Algorithm selection

dewdrops auto-selects the right algorithm based on your graph:

- **No weights on any node** → BFS. Integer hop counts. Optimal for unweighted graphs.
- **Any node has weights** → Dijkstra. Float costs. Optimal for weighted graphs.

You never configure this. It just dews it.

---

## API

### `TreeNode`

```typescript
interface TreeNode {
  id: string
  connections: string[]       // neighbor node ids
  weights: Record<string, number>  // neighbor id → edge cost
}
```

### `PathResult`

```typescript
interface PathResult {
  distance: number        // total cost, or -1 if unreachable
  path: string[] | null   // ordered node ids, or null if unreachable
}
```

### `NearestResult`

```typescript
interface NearestResult {
  target_id: string | null  // id of nearest reachable candidate, or null
  distance: number          // -1 if none reachable
  path: string[] | null     // path to nearest, or null
}
```

### `TreeTopologyHeuristics.findPath(graph, start, target)`

Shortest path between two nodes. BFS or Dijkstra, auto-selected.
Returns `PathResult` with `distance: -1` and `path: null` if unreachable.

### `TreeTopologyHeuristics.findNearest(graph, start, candidates)`

Nearest reachable node from a candidate set.
Returns `NearestResult` with `target_id: null` if none are reachable.

### `TreeTopologyHeuristics.calculateGraphDistance(graph, start, target)`

Shortest distance as a number. Returns `-1` if unreachable.

---

## Zero dependencies

No runtime dependencies. BFS and Dijkstra implemented from scratch with an inline binary min-heap. Works in Node, browsers, and any TypeScript environment.

---

## Part of Dew

dewdrops is the TypeScript distro of [Dew](https://whatcanidew.com) — intent-driven graph routing for any connected system.

> "What do you need it to dew?"
