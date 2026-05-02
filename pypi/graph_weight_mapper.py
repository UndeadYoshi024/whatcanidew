"""
graph_weight_mapper
===================
Applies a ConstraintProfile to a graph of TreeNode objects before routing runs.
Shapes the terrain. Dijkstra finds the river.

hard_block nodes are removed entirely — Dijkstra never sees them.
avoid nodes are penalized (edge cost × penalty_factor, default 10×).
prefer nodes are rewarded (edge cost × reward_factor, default 0.5×).
All edges get a composite cost from the profile's weight dimensions.

The input graph is never mutated — apply_weights deep copies before modifying.

Usage:
    from graph_weight_mapper import apply_weights
    modified_graph = apply_weights(graph, profile)
"""
from __future__ import annotations
import copy
from typing import Dict, List
from tree_topology_heuristics import TreeNode
from intent_weight_synthesizer import ConstraintProfile


def apply_weights(
    graph: Dict[str, TreeNode],
    profile: ConstraintProfile,
    penalty_factor: float = 10.0,
    reward_factor: float = 0.5,
) -> Dict[str, TreeNode]:
    g = copy.deepcopy(graph)

    for blocked_id in profile.constraints.get("hard_block", []):
        g.pop(blocked_id, None)
        for node in g.values():
            if blocked_id in node.connections:
                node.connections.remove(blocked_id)
            node.weights.pop(blocked_id, None)

    for node in g.values():
        for neighbor_id in node.connections:
            if neighbor_id not in node.weights:
                node.weights[neighbor_id] = 1.0
            base_cost = node.weights[neighbor_id]
            composite = sum(profile.weights[dim] * base_cost for dim in profile.weights)
            node.weights[neighbor_id] = composite

    for avoid_id in profile.constraints.get("avoid", []):
        for node in g.values():
            if avoid_id in node.connections:
                node.weights[avoid_id] = node.weights[avoid_id] * penalty_factor

    for prefer_id in profile.constraints.get("prefer", []):
        for node in g.values():
            if prefer_id in node.connections:
                node.weights[prefer_id] = node.weights[prefer_id] * reward_factor

    return g
