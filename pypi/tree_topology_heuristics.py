"""
tree_topology_heuristics
========================
Shortest path between any two nodes in any connected graph.
BFS for unweighted graphs. Dijkstra for weighted graphs.
Path reconstruction. Multi-target nearest-node search.

Install:
    pip install tree-topology-heuristics

Usage:
    from tree_topology_heuristics import TreeTopologyHeuristics, TreeNode

    graph = {
        "a": TreeNode(id="a", connections=["b", "c"]),
        "b": TreeNode(id="b", connections=["a", "d"]),
        "c": TreeNode(id="c", connections=["a", "d"]),
        "d": TreeNode(id="d", connections=["b", "c"]),
    }

    distance = TreeTopologyHeuristics.calculate_graph_distance(graph, "a", "d")
    result   = TreeTopologyHeuristics.find_path(graph, "a", "d")
    nearest  = TreeTopologyHeuristics.find_nearest(graph, "a", ["c", "d"])
"""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from heapq import heappush, heappop
from typing import Dict, List, Optional, Tuple


@dataclass
class TreeNode:
    id: str
    connections: List[str]
    weights: Dict[str, float] = field(default_factory=dict)  # neighbor id → edge cost


@dataclass
class PathResult:
    distance: float          # total cost, or -1 if unreachable
    path: Optional[List[str]]  # ordered node ids, or None


@dataclass
class NearestResult:
    target_id: Optional[str]
    distance: float
    path: Optional[List[str]]


def _reconstruct(parents: Dict[str, Optional[str]], start: str, target: str) -> List[str]:
    path = []
    current: Optional[str] = target
    while current is not None:
        path.append(current)
        current = parents.get(current)
    path.reverse()
    return path


def _bfs(graph: Dict[str, TreeNode], start: str, target: str) -> PathResult:
    queue: deque[str] = deque([start])
    visited = {start}
    parents: Dict[str, Optional[str]] = {start: None}
    dist: Dict[str, int] = {start: 0}

    while queue:
        current = queue.popleft()
        current_dist = dist[current]
        node = graph.get(current)
        if not node:
            continue
        for neighbor in node.connections:
            if neighbor in visited:
                continue
            visited.add(neighbor)
            parents[neighbor] = current
            dist[neighbor] = current_dist + 1
            if neighbor == target:
                return PathResult(
                    distance=current_dist + 1,
                    path=_reconstruct(parents, start, target)
                )
            queue.append(neighbor)

    return PathResult(distance=-1, path=None)


def _dijkstra(graph: Dict[str, TreeNode], start: str, target: str) -> PathResult:
    heap: List[Tuple[float, str]] = [(0.0, start)]
    dist: Dict[str, float] = {start: 0.0}
    parents: Dict[str, Optional[str]] = {start: None}

    while heap:
        cost, current = heappop(heap)
        if cost > dist.get(current, float("inf")):
            continue
        if current == target:
            return PathResult(
                distance=cost,
                path=_reconstruct(parents, start, target)
            )
        node = graph.get(current)
        if not node:
            continue
        for neighbor in node.connections:
            edge_cost = node.weights.get(neighbor, 1.0)
            new_cost = cost + edge_cost
            if new_cost < dist.get(neighbor, float("inf")):
                dist[neighbor] = new_cost
                parents[neighbor] = current
                heappush(heap, (new_cost, neighbor))

    return PathResult(distance=-1, path=None)


class TreeTopologyHeuristics:

    @staticmethod
    def calculate_graph_distance(
        graph: Dict[str, TreeNode],
        start_node_id: str,
        target_node_id: str
    ) -> float:
        """Shortest hop distance. Returns -1 if unreachable."""
        return TreeTopologyHeuristics.find_path(graph, start_node_id, target_node_id).distance

    @staticmethod
    def find_path(
        graph: Dict[str, TreeNode],
        start_node_id: str,
        target_node_id: str
    ) -> PathResult:
        """Shortest path with route reconstruction. BFS or Dijkstra auto-selected."""
        if start_node_id not in graph or target_node_id not in graph:
            return PathResult(distance=-1, path=None)
        if start_node_id == target_node_id:
            return PathResult(distance=0, path=[start_node_id])

        has_weights = any(bool(n.weights) for n in graph.values())
        if has_weights:
            return _dijkstra(graph, start_node_id, target_node_id)
        return _bfs(graph, start_node_id, target_node_id)

    @staticmethod
    def find_nearest(
        graph: Dict[str, TreeNode],
        start_node_id: str,
        target_node_ids: List[str]
    ) -> NearestResult:
        """Find the nearest reachable node from a set of candidates."""
        if start_node_id not in graph or not target_node_ids:
            return NearestResult(target_id=None, distance=-1, path=None)

        best = NearestResult(target_id=None, distance=-1, path=None)
        for target_id in target_node_ids:
            result = TreeTopologyHeuristics.find_path(graph, start_node_id, target_id)
            if result.distance == -1:
                continue
            if best.distance == -1 or result.distance < best.distance:
                best = NearestResult(
                    target_id=target_id,
                    distance=result.distance,
                    path=result.path
                )
        return best
