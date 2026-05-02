"""
test_weight_mapper.py
=====================
Tests for graph_weight_mapper.py.
Proves that hard_block, avoid, prefer, and composite cost all behave
exactly as specified. The terrain shaping is load-bearing.
"""

import pytest
from graph_weight_mapper import apply_weights
from tree_topology_heuristics import TreeNode, TreeTopologyHeuristics
from intent_weight_synthesizer import ConstraintProfile


def make_profile(
    avoid=None, prefer=None, hard_block=None,
    weights=None, name="test_profile"
):
    return ConstraintProfile(
        profile_name=name,
        intent_summary="test",
        weights=weights or {"time": 0.2, "cost": 0.2, "risk": 0.2, "reliability": 0.2, "distance": 0.2},
        constraints={
            "avoid": avoid or [],
            "prefer": prefer or [],
            "hard_block": hard_block or [],
        },
        notes="",
        raw_intent="test"
    )


class TestHardBlock:

    def test_hard_blocked_node_removed_from_graph(self, simple_graph):
        profile = make_profile(hard_block=["b"])
        result = apply_weights(simple_graph, profile)
        assert "b" not in result

    def test_hard_blocked_node_removed_from_connections(self, simple_graph):
        profile = make_profile(hard_block=["b"])
        result = apply_weights(simple_graph, profile)
        for node in result.values():
            assert "b" not in node.connections

    def test_hard_blocked_makes_path_unreachable(self, simple_graph):
        """a→b→c→d: block b makes d unreachable from a."""
        profile = make_profile(hard_block=["b"])
        result = apply_weights(simple_graph, profile)
        path = TreeTopologyHeuristics.find_path(result, "a", "d")
        assert path.distance == -1

    def test_hard_block_nonexistent_node_is_safe(self, simple_graph):
        """Blocking a node that doesn't exist should not crash."""
        profile = make_profile(hard_block=["GHOST_NODE"])
        result = apply_weights(simple_graph, profile)
        assert "a" in result  # graph intact

    def test_multiple_hard_blocks(self, hospital_graph):
        profile = make_profile(hard_block=["maintenance_01", "radiology"])
        result = apply_weights(hospital_graph, profile)
        assert "maintenance_01" not in result
        assert "radiology" not in result

    def test_original_graph_not_mutated(self, simple_graph):
        original_keys = set(simple_graph.keys())
        profile = make_profile(hard_block=["b"])
        apply_weights(simple_graph, profile)
        assert set(simple_graph.keys()) == original_keys


class TestAvoidPenalty:

    def test_avoid_increases_edge_cost(self, diamond_graph):
        """Avoid c: edge cost to c should be multiplied by penalty_factor."""
        profile = make_profile(avoid=["c"])
        result = apply_weights(diamond_graph, profile, penalty_factor=10.0)
        # Node a's edge to c should be heavily penalized
        assert result["a"].weights.get("c", 0) > result["a"].weights.get("b", 0)

    def test_avoid_causes_dijkstra_to_route_around(self, diamond_graph):
        """Diamond graph: avoid c → Dijkstra should route a→b→d."""
        profile = make_profile(avoid=["c"])
        result = apply_weights(diamond_graph, profile, penalty_factor=100.0)
        path = TreeTopologyHeuristics.find_path(result, "a", "d")
        assert "c" not in path.path

    def test_avoid_does_not_remove_node(self, diamond_graph):
        """Avoid ≠ hard_block. Node stays in graph."""
        profile = make_profile(avoid=["c"])
        result = apply_weights(diamond_graph, profile)
        assert "c" in result

    def test_avoid_nonexistent_node_is_safe(self, simple_graph):
        profile = make_profile(avoid=["GHOST"])
        result = apply_weights(simple_graph, profile)
        assert "a" in result


class TestPreferReward:

    def test_prefer_decreases_edge_cost(self, diamond_graph):
        """Prefer b: edge cost to b should be lower than to c."""
        profile = make_profile(prefer=["b"])
        result = apply_weights(diamond_graph, profile, reward_factor=0.1)
        assert result["a"].weights.get("b", 1) < result["a"].weights.get("c", 1)

    def test_prefer_causes_dijkstra_to_route_through(self, diamond_graph):
        """Diamond: prefer b → Dijkstra should route a→b→d."""
        profile = make_profile(prefer=["b"])
        result = apply_weights(diamond_graph, profile, reward_factor=0.01)
        path = TreeTopologyHeuristics.find_path(result, "a", "d")
        assert "b" in path.path

    def test_prefer_nonexistent_node_is_safe(self, simple_graph):
        profile = make_profile(prefer=["GHOST"])
        result = apply_weights(simple_graph, profile)
        assert "a" in result


class TestCompositeCost:

    def test_composite_cost_applied_to_all_edges(self, simple_graph):
        """All edges should have composite weights after apply_weights."""
        profile = make_profile()
        result = apply_weights(simple_graph, profile)
        for node in result.values():
            for neighbor in node.connections:
                assert neighbor in node.weights
                assert node.weights[neighbor] > 0

    def test_composite_cost_is_deterministic(self, simple_graph):
        """Same profile applied twice should produce identical weights."""
        profile = make_profile()
        result1 = apply_weights(simple_graph, profile)
        result2 = apply_weights(simple_graph, profile)
        for node_id in result1:
            assert result1[node_id].weights == result2[node_id].weights

    def test_deep_copy_no_mutation(self, weighted_graph):
        """apply_weights must not mutate the original graph weights."""
        original_weight = weighted_graph["a"].weights.get("b")
        profile = make_profile(avoid=["b"])
        apply_weights(weighted_graph, profile, penalty_factor=50.0)
        assert weighted_graph["a"].weights.get("b") == original_weight


class TestHospitalProfile:

    def test_hospital_profile_blocks_maintenance(self, hospital_graph, hospital_profile):
        result = apply_weights(hospital_graph, hospital_profile)
        assert "maintenance_01" not in result

    def test_hospital_profile_prefers_standard_beds(self, hospital_graph, hospital_profile):
        result = apply_weights(hospital_graph, hospital_profile)
        # bed_01 and bed_03 should have lower incoming cost than bed_02
        bed_01_cost = result["triage"].weights.get("bed_01", float("inf"))
        bed_02_cost = result["triage"].weights.get("bed_02", float("inf"))
        assert bed_01_cost < bed_02_cost

    def test_hospital_profile_routes_patient_to_preferred_bed(self, hospital_graph, hospital_profile):
        result = apply_weights(hospital_graph, hospital_profile)
        path = TreeTopologyHeuristics.find_nearest(
            result, "triage", ["bed_01", "bed_02", "bed_03"]
        )
        # Should land on a preferred bed (bed_01 or bed_03)
        assert path.target_id in ("bed_01", "bed_03")
