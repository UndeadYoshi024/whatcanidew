"""
test_core.py
============
Unit tests for tree_topology_heuristics.py.
Covers BFS, Dijkstra, auto-selection, edge cases, find_nearest.
The core math never touches. These tests prove it.
"""

import pytest
from tree_topology_heuristics import TreeTopologyHeuristics, TreeNode, PathResult


class TestFindPath:

    def test_bfs_simple_path(self, simple_graph):
        result = TreeTopologyHeuristics.find_path(simple_graph, "a", "d")
        assert result.distance == 3
        assert result.path == ["a", "b", "c", "d"]

    def test_bfs_adjacent(self, simple_graph):
        result = TreeTopologyHeuristics.find_path(simple_graph, "a", "b")
        assert result.distance == 1
        assert result.path == ["a", "b"]

    def test_same_node_returns_zero(self, simple_graph):
        result = TreeTopologyHeuristics.find_path(simple_graph, "a", "a")
        assert result.distance == 0
        assert result.path == ["a"]

    def test_disconnected_returns_negative_one(self, disconnected_graph):
        result = TreeTopologyHeuristics.find_path(disconnected_graph, "a", "x")
        assert result.distance == -1
        assert result.path is None

    def test_unknown_start_returns_negative_one(self, simple_graph):
        result = TreeTopologyHeuristics.find_path(simple_graph, "GHOST", "d")
        assert result.distance == -1
        assert result.path is None

    def test_unknown_target_returns_negative_one(self, simple_graph):
        result = TreeTopologyHeuristics.find_path(simple_graph, "a", "GHOST")
        assert result.distance == -1
        assert result.path is None

    def test_bfs_diamond_finds_shortest(self, diamond_graph):
        result = TreeTopologyHeuristics.find_path(diamond_graph, "a", "d")
        assert result.distance == 2
        assert result.path[0] == "a"
        assert result.path[-1] == "d"
        assert len(result.path) == 3

    def test_dijkstra_auto_selected_on_weights(self, weighted_graph):
        result = TreeTopologyHeuristics.find_path(weighted_graph, "a", "d")
        # a→b→d costs 2.0, a→c→d costs 6.0 — Dijkstra picks a→b→d
        assert result.path == ["a", "b", "d"]
        assert result.distance == pytest.approx(2.0)

    def test_dijkstra_avoids_expensive_path(self, weighted_graph):
        result = TreeTopologyHeuristics.find_path(weighted_graph, "a", "d")
        assert "c" not in result.path

    def test_single_node_to_itself(self, single_node_graph):
        result = TreeTopologyHeuristics.find_path(single_node_graph, "solo", "solo")
        assert result.distance == 0
        assert result.path == ["solo"]

    def test_path_starts_at_start(self, simple_graph):
        result = TreeTopologyHeuristics.find_path(simple_graph, "b", "d")
        assert result.path[0] == "b"

    def test_path_ends_at_target(self, simple_graph):
        result = TreeTopologyHeuristics.find_path(simple_graph, "b", "d")
        assert result.path[-1] == "d"

    def test_path_is_contiguous(self, simple_graph):
        """Every step in the path must be a valid connection."""
        result = TreeTopologyHeuristics.find_path(simple_graph, "a", "d")
        for i in range(len(result.path) - 1):
            current = result.path[i]
            nxt = result.path[i + 1]
            assert nxt in simple_graph[current].connections, \
                f"{nxt} not connected to {current}"


class TestCalculateGraphDistance:

    def test_matches_find_path_distance(self, simple_graph):
        dist = TreeTopologyHeuristics.calculate_graph_distance(simple_graph, "a", "d")
        path_result = TreeTopologyHeuristics.find_path(simple_graph, "a", "d")
        assert dist == path_result.distance

    def test_returns_negative_one_when_disconnected(self, disconnected_graph):
        dist = TreeTopologyHeuristics.calculate_graph_distance(disconnected_graph, "a", "x")
        assert dist == -1

    def test_zero_for_same_node(self, simple_graph):
        dist = TreeTopologyHeuristics.calculate_graph_distance(simple_graph, "c", "c")
        assert dist == 0


class TestFindNearest:

    def test_finds_closer_of_two(self, simple_graph):
        # from b: c is 1 hop, d is 2 hops
        result = TreeTopologyHeuristics.find_nearest(simple_graph, "b", ["c", "d"])
        assert result.target_id == "c"
        assert result.distance == 1

    def test_finds_only_reachable(self, disconnected_graph):
        # a can reach b but not x or y
        result = TreeTopologyHeuristics.find_nearest(disconnected_graph, "a", ["b", "x", "y"])
        assert result.target_id == "b"
        assert result.distance == 1

    def test_returns_none_when_all_unreachable(self, disconnected_graph):
        result = TreeTopologyHeuristics.find_nearest(disconnected_graph, "a", ["x", "y"])
        assert result.target_id is None
        assert result.distance == -1
        assert result.path is None

    def test_empty_candidates(self, simple_graph):
        result = TreeTopologyHeuristics.find_nearest(simple_graph, "a", [])
        assert result.target_id is None
        assert result.distance == -1

    def test_unknown_start(self, simple_graph):
        result = TreeTopologyHeuristics.find_nearest(simple_graph, "GHOST", ["a", "b"])
        assert result.target_id is None
        assert result.distance == -1

    def test_path_reconstruction_on_nearest(self, simple_graph):
        result = TreeTopologyHeuristics.find_nearest(simple_graph, "a", ["c", "d"])
        assert result.path is not None
        assert result.path[0] == "a"
        assert result.path[-1] == result.target_id

    def test_single_candidate(self, simple_graph):
        result = TreeTopologyHeuristics.find_nearest(simple_graph, "a", ["d"])
        assert result.target_id == "d"
        assert result.distance == 3

    def test_candidate_is_start_node(self, simple_graph):
        result = TreeTopologyHeuristics.find_nearest(simple_graph, "a", ["a", "d"])
        assert result.target_id == "a"
        assert result.distance == 0


class TestAlgorithmAutoSelection:

    def test_unweighted_uses_bfs(self):
        """Unweighted graph: BFS returns integer hop counts."""
        graph = {
            "a": TreeNode(id="a", connections=["b"]),
            "b": TreeNode(id="b", connections=["a"]),
        }
        result = TreeTopologyHeuristics.find_path(graph, "a", "b")
        assert result.distance == 1

    def test_weighted_uses_dijkstra(self):
        """Weighted graph: Dijkstra returns float cost."""
        graph = {
            "a": TreeNode(id="a", connections=["b"], weights={"b": 3.7}),
            "b": TreeNode(id="b", connections=["a"], weights={"a": 3.7}),
        }
        result = TreeTopologyHeuristics.find_path(graph, "a", "b")
        assert result.distance == pytest.approx(3.7)

    def test_partial_weights_triggers_dijkstra(self):
        """Even one node with weights should trigger Dijkstra."""
        graph = {
            "a": TreeNode(id="a", connections=["b"], weights={"b": 2.0}),
            "b": TreeNode(id="b", connections=["a", "c"]),
            "c": TreeNode(id="c", connections=["b"]),
        }
        result = TreeTopologyHeuristics.find_path(graph, "a", "c")
        # a→b costs 2.0 (weighted), b→c costs 1.0 (default)
        assert result.distance == pytest.approx(3.0)
