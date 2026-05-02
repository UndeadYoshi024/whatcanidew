"""
Tests for repoe_adapter.

Covers build_graph, find_disconnected, and merge.
Does NOT test load() — it uses interactive input() and is covered in Stage 8 live test.
"""

import copy
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pypi"))

from tree_topology_heuristics import TreeNode
from repoe_adapter import build_graph, find_disconnected, merge


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _minimal_repoe():
    return {"a": "b", "b": "a", "c": "a"}


def _array_repoe():
    return {"x": ["y", "z"], "y": "x", "z": "x"}


def _connected_graph():
    return {
        "a": TreeNode(id="a", connections=["b", "c"], weights={"b": 1.0, "c": 1.0}),
        "b": TreeNode(id="b", connections=["a"], weights={"a": 1.0}),
        "c": TreeNode(id="c", connections=["a"], weights={"a": 1.0}),
    }


def _disconnected_graph():
    # Components: {a, b, c} (size 3), {d, e} (size 2), {f} (size 1)
    return {
        "a": TreeNode(id="a", connections=["b"], weights={"b": 1.0}),
        "b": TreeNode(id="b", connections=["a", "c"], weights={"a": 1.0, "c": 1.0}),
        "c": TreeNode(id="c", connections=["b"], weights={"b": 1.0}),
        "d": TreeNode(id="d", connections=["e"], weights={"e": 1.0}),
        "e": TreeNode(id="e", connections=["d"], weights={"d": 1.0}),
        "f": TreeNode(id="f", connections=[], weights={}),
    }


def _base_graph():
    return {
        "a": TreeNode(id="a", connections=["b"], weights={"b": 1.0}),
        "b": TreeNode(id="b", connections=["a"], weights={"a": 1.0}),
    }


def _extra_connections():
    # Introduces node c; a gains edge to c
    return {
        "a": TreeNode(id="a", connections=["c"], weights={"c": 1.0}),
        "c": TreeNode(id="c", connections=["a"], weights={"a": 1.0}),
    }


# ---------------------------------------------------------------------------
# build_graph — basic structure
# ---------------------------------------------------------------------------

def test_build_graph_returns_dict():
    assert isinstance(build_graph(_minimal_repoe()), dict)


def test_build_graph_values_are_tree_nodes():
    graph = build_graph(_minimal_repoe())
    for node in graph.values():
        assert isinstance(node, TreeNode)


def test_build_graph_all_keys_become_nodes():
    graph = build_graph(_minimal_repoe())
    assert set(graph.keys()) == {"a", "b", "c"}


def test_build_graph_node_id_matches_key():
    graph = build_graph(_minimal_repoe())
    for key, node in graph.items():
        assert node.id == key


# ---------------------------------------------------------------------------
# build_graph — string value → edge
# ---------------------------------------------------------------------------

def test_string_matching_key_produces_edge():
    # "a": "b" — "b" is a top-level key
    graph = build_graph(_minimal_repoe())
    assert "b" in graph["a"].connections


def test_string_matching_key_weight_is_1_0():
    graph = build_graph(_minimal_repoe())
    assert graph["a"].weights["b"] == 1.0


def test_string_matching_key_weight_type_is_float():
    graph = build_graph(_minimal_repoe())
    assert isinstance(graph["a"].weights["b"], float)


def test_nonmatching_string_produces_no_edge():
    repoe = {"p": "does_not_exist", "q": "also_missing"}
    graph = build_graph(repoe)
    assert graph["p"].connections == []
    assert graph["q"].connections == []


def test_nonmatching_string_produces_no_weights():
    repoe = {"p": "does_not_exist", "q": "also_missing"}
    graph = build_graph(repoe)
    assert graph["p"].weights == {}
    assert graph["q"].weights == {}


# ---------------------------------------------------------------------------
# build_graph — array of strings → edges
# ---------------------------------------------------------------------------

def test_array_matching_keys_produces_edge_for_each():
    graph = build_graph(_array_repoe())
    assert "y" in graph["x"].connections
    assert "z" in graph["x"].connections


def test_array_edges_each_have_weight_1_0():
    graph = build_graph(_array_repoe())
    assert graph["x"].weights["y"] == 1.0
    assert graph["x"].weights["z"] == 1.0


def test_array_edge_weights_are_float():
    graph = build_graph(_array_repoe())
    for neighbor_id in ["y", "z"]:
        assert isinstance(graph["x"].weights[neighbor_id], float)


def test_array_partial_match_only_adds_matching_entries():
    repoe = {"a": ["b", "nonexistent"], "b": "a"}
    graph = build_graph(repoe)
    assert "b" in graph["a"].connections
    assert "nonexistent" not in graph["a"].connections
    assert "nonexistent" not in graph["a"].weights


# ---------------------------------------------------------------------------
# build_graph — non-string / non-list values produce no edges
# ---------------------------------------------------------------------------

def test_integer_value_produces_no_edges():
    repoe = {"a": 42, "b": "a"}
    graph = build_graph(repoe)
    assert graph["a"].connections == []
    assert graph["a"].weights == {}


def test_boolean_value_produces_no_edges():
    repoe = {"a": True, "b": "a"}
    graph = build_graph(repoe)
    assert graph["a"].connections == []
    assert graph["a"].weights == {}


def test_float_value_produces_no_edges():
    repoe = {"a": 3.14, "b": "a"}
    graph = build_graph(repoe)
    assert graph["a"].connections == []
    assert graph["a"].weights == {}


def test_none_value_produces_no_edges():
    repoe = {"a": None, "b": "a"}
    graph = build_graph(repoe)
    assert graph["a"].connections == []
    assert graph["a"].weights == {}


def test_all_non_edge_types_together_produce_no_edges():
    repoe = {"alpha": 42, "beta": True, "gamma": 3.14, "delta": None}
    graph = build_graph(repoe)
    for node in graph.values():
        assert node.connections == []
        assert node.weights == {}


# ---------------------------------------------------------------------------
# build_graph — purity
# ---------------------------------------------------------------------------

def test_build_graph_does_not_mutate_input():
    repoe = {"a": "b", "b": "a"}
    snapshot = copy.deepcopy(repoe)
    build_graph(repoe)
    assert repoe == snapshot


def test_build_graph_is_deterministic():
    repoe = {"a": "b", "b": ["a", "c"], "c": "b"}
    g1 = build_graph(repoe)
    g2 = build_graph(repoe)
    for key in g1:
        assert g1[key].id == g2[key].id
        assert sorted(g1[key].connections) == sorted(g2[key].connections)
        assert g1[key].weights == g2[key].weights


# ---------------------------------------------------------------------------
# find_disconnected
# ---------------------------------------------------------------------------

def test_find_disconnected_fully_connected_returns_empty_list():
    assert find_disconnected(_connected_graph()) == []


def test_find_disconnected_single_node_returns_empty_list():
    graph = {"a": TreeNode(id="a", connections=[], weights={})}
    assert find_disconnected(graph) == []


def test_find_disconnected_returns_correct_component_count():
    result = find_disconnected(_disconnected_graph())
    assert len(result) == 3  # {a,b,c}, {d,e}, {f}


def test_find_disconnected_each_component_is_list_of_str():
    result = find_disconnected(_disconnected_graph())
    for component in result:
        assert isinstance(component, list)
        for node_id in component:
            assert isinstance(node_id, str)


def test_find_disconnected_largest_component_first():
    result = find_disconnected(_disconnected_graph())
    sizes = [len(c) for c in result]
    assert sizes[0] == max(sizes)


def test_find_disconnected_all_node_ids_accounted_for():
    graph = _disconnected_graph()
    result = find_disconnected(graph)
    all_ids = {node_id for component in result for node_id in component}
    assert all_ids == set(graph.keys())


def test_find_disconnected_components_are_disjoint():
    result = find_disconnected(_disconnected_graph())
    seen = set()
    for component in result:
        for node_id in component:
            assert node_id not in seen, f"{node_id} appeared in multiple components"
            seen.add(node_id)


def test_find_disconnected_two_isolated_nodes_returns_two_components():
    graph = {
        "a": TreeNode(id="a", connections=[], weights={}),
        "b": TreeNode(id="b", connections=[], weights={}),
    }
    result = find_disconnected(graph)
    assert len(result) == 2


def test_find_disconnected_correct_ids_in_components():
    result = find_disconnected(_disconnected_graph())
    all_by_id = {frozenset(c) for c in result}
    assert frozenset({"a", "b", "c"}) in all_by_id
    assert frozenset({"d", "e"}) in all_by_id
    assert frozenset({"f"}) in all_by_id


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

def test_merge_does_not_mutate_input_graph():
    base = _base_graph()
    original_a_connections = list(base["a"].connections)
    original_keys = set(base.keys())
    merge(base, _extra_connections())
    assert base["a"].connections == original_a_connections
    assert set(base.keys()) == original_keys


def test_merge_returns_new_graph_object():
    base = _base_graph()
    merged = merge(base, _extra_connections())
    assert merged is not base


def test_merge_preserves_original_edges():
    merged = merge(_base_graph(), _extra_connections())
    assert "b" in merged["a"].connections


def test_merge_adds_new_edges():
    merged = merge(_base_graph(), _extra_connections())
    assert "c" in merged["a"].connections


def test_merge_adds_new_nodes():
    merged = merge(_base_graph(), _extra_connections())
    assert "c" in merged


def test_merge_roundtrip_all_edges_present():
    merged = merge(_base_graph(), _extra_connections())
    # From base: a→b, b→a
    assert "b" in merged["a"].connections
    assert "a" in merged["b"].connections
    # From extra: a→c, c→a
    assert "c" in merged["a"].connections
    assert "a" in merged["c"].connections


def test_merge_new_edges_have_weight_1_0():
    merged = merge(_base_graph(), _extra_connections())
    assert merged["a"].weights["c"] == 1.0


def test_merge_new_edge_weights_are_float():
    merged = merge(_base_graph(), _extra_connections())
    assert isinstance(merged["a"].weights["c"], float)


def test_merge_preserves_existing_weights():
    merged = merge(_base_graph(), _extra_connections())
    assert merged["a"].weights["b"] == 1.0
    assert isinstance(merged["a"].weights["b"], float)


def test_merge_empty_extra_returns_equivalent_graph():
    base = _base_graph()
    merged = merge(base, {})
    assert set(merged.keys()) == set(base.keys())
    for key in base:
        assert sorted(merged[key].connections) == sorted(base[key].connections)
        assert merged[key].weights == base[key].weights
