// dewdrops — tree topology heuristics
// Shortest path between any two nodes in any connected graph.
// BFS for unweighted graphs. Dijkstra for weighted graphs.
// Path reconstruction. Multi-target nearest-node search.

export interface TreeNode {
  id: string;
  connections: string[];
  weights: Record<string, number>;
}

export interface PathResult {
  distance: number;
  path: string[] | null;
}

export interface NearestResult {
  target_id: string | null;
  distance: number;
  path: string[] | null;
}

type Graph = Record<string, TreeNode>;

function reconstruct(
  parents: Map<string, string | null>,
  target: string
): string[] {
  const path: string[] = [];
  let current: string | null | undefined = target;
  while (current != null) {
    path.push(current);
    current = parents.get(current) ?? null;
  }
  path.reverse();
  return path;
}

function bfs(graph: Graph, start: string, target: string): PathResult {
  const queue: string[] = [start];
  const visited = new Set<string>([start]);
  const parents = new Map<string, string | null>([[start, null]]);
  const dist = new Map<string, number>([[start, 0]]);

  let head = 0;
  while (head < queue.length) {
    const current = queue[head++];
    const currentDist = dist.get(current)!;
    const node = graph[current];
    if (!node) continue;

    for (const neighbor of node.connections) {
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);
      parents.set(neighbor, current);
      dist.set(neighbor, currentDist + 1);

      if (neighbor === target) {
        return {
          distance: currentDist + 1,
          path: reconstruct(parents, target),
        };
      }
      queue.push(neighbor);
    }
  }

  return { distance: -1, path: null };
}

function dijkstra(graph: Graph, start: string, target: string): PathResult {
  // Min-heap entries: [cost, nodeId]
  const heap: [number, string][] = [[0, start]];
  const dist = new Map<string, number>([[start, 0]]);
  const parents = new Map<string, string | null>([[start, null]]);

  while (heap.length > 0) {
    // Extract minimum — simple binary min-heap
    const [cost, current] = heapPop(heap);

    if (cost > (dist.get(current) ?? Infinity)) continue;

    if (current === target) {
      return { distance: cost, path: reconstruct(parents, target) };
    }

    const node = graph[current];
    if (!node) continue;

    for (const neighbor of node.connections) {
      const edgeCost = node.weights[neighbor] ?? 1.0;
      const newCost = cost + edgeCost;
      if (newCost < (dist.get(neighbor) ?? Infinity)) {
        dist.set(neighbor, newCost);
        parents.set(neighbor, current);
        heapPush(heap, [newCost, neighbor]);
      }
    }
  }

  return { distance: -1, path: null };
}

// Inline binary min-heap keyed on the first element of each tuple.
function heapPush(heap: [number, string][], item: [number, string]): void {
  heap.push(item);
  let i = heap.length - 1;
  while (i > 0) {
    const parent = (i - 1) >> 1;
    if (heap[parent][0] <= heap[i][0]) break;
    [heap[parent], heap[i]] = [heap[i], heap[parent]];
    i = parent;
  }
}

function heapPop(heap: [number, string][]): [number, string] {
  const top = heap[0];
  const last = heap.pop()!;
  if (heap.length > 0) {
    heap[0] = last;
    let i = 0;
    const n = heap.length;
    while (true) {
      let smallest = i;
      const l = 2 * i + 1;
      const r = 2 * i + 2;
      if (l < n && heap[l][0] < heap[smallest][0]) smallest = l;
      if (r < n && heap[r][0] < heap[smallest][0]) smallest = r;
      if (smallest === i) break;
      [heap[i], heap[smallest]] = [heap[smallest], heap[i]];
      i = smallest;
    }
  }
  return top;
}

export class TreeTopologyHeuristics {
  static findPath(graph: Graph, startNodeId: string, targetNodeId: string): PathResult {
    if (!(startNodeId in graph) || !(targetNodeId in graph)) {
      return { distance: -1, path: null };
    }
    if (startNodeId === targetNodeId) {
      return { distance: 0, path: [startNodeId] };
    }

    const hasWeights = Object.values(graph).some(
      (n) => Object.keys(n.weights).length > 0
    );

    return hasWeights
      ? dijkstra(graph, startNodeId, targetNodeId)
      : bfs(graph, startNodeId, targetNodeId);
  }

  static findNearest(
    graph: Graph,
    startNodeId: string,
    targetNodeIds: string[]
  ): NearestResult {
    if (!(startNodeId in graph) || targetNodeIds.length === 0) {
      return { target_id: null, distance: -1, path: null };
    }

    let best: NearestResult = { target_id: null, distance: -1, path: null };

    for (const targetId of targetNodeIds) {
      const result = TreeTopologyHeuristics.findPath(graph, startNodeId, targetId);
      if (result.distance === -1) continue;
      if (best.distance === -1 || result.distance < best.distance) {
        best = { target_id: targetId, distance: result.distance, path: result.path };
      }
    }

    return best;
  }

  static calculateGraphDistance(
    graph: Graph,
    startNodeId: string,
    targetNodeId: string
  ): number {
    return TreeTopologyHeuristics.findPath(graph, startNodeId, targetNodeId).distance;
  }
}
