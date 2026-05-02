"""
conftest.py
===========
Shared fixtures for the Dew test suite.
Graphs, profiles, temp log paths — one place, used everywhere.
"""

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Make root importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from tree_topology_heuristics import TreeNode
from intent_weight_synthesizer import ConstraintProfile
from logger import ActivityLog


# ---------------------------------------------------------------------------
# Graphs
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_graph():
    """Linear chain: a → b → c → d"""
    return {
        "a": TreeNode(id="a", connections=["b"]),
        "b": TreeNode(id="b", connections=["a", "c"]),
        "c": TreeNode(id="c", connections=["b", "d"]),
        "d": TreeNode(id="d", connections=["c"]),
    }


@pytest.fixture
def diamond_graph():
    """
    Diamond: a → b → d
                  ↘ c → d
    Two equal-length paths from a to d.
    """
    return {
        "a": TreeNode(id="a", connections=["b", "c"]),
        "b": TreeNode(id="b", connections=["a", "d"]),
        "c": TreeNode(id="c", connections=["a", "d"]),
        "d": TreeNode(id="d", connections=["b", "c"]),
    }


@pytest.fixture
def weighted_graph():
    """
    Weighted: a → b (cost 1) → d (cost 1)  total = 2
              a → c (cost 5) → d (cost 1)  total = 6
    Dijkstra should prefer a → b → d.
    """
    return {
        "a": TreeNode(id="a", connections=["b", "c"], weights={"b": 1.0, "c": 5.0}),
        "b": TreeNode(id="b", connections=["a", "d"], weights={"a": 1.0, "d": 1.0}),
        "c": TreeNode(id="c", connections=["a", "d"], weights={"a": 5.0, "d": 1.0}),
        "d": TreeNode(id="d", connections=["b", "c"], weights={"b": 1.0, "c": 1.0}),
    }


@pytest.fixture
def disconnected_graph():
    """Two isolated islands — no path between them."""
    return {
        "a": TreeNode(id="a", connections=["b"]),
        "b": TreeNode(id="b", connections=["a"]),
        "x": TreeNode(id="x", connections=["y"]),
        "y": TreeNode(id="y", connections=["x"]),
    }


@pytest.fixture
def single_node_graph():
    return {"solo": TreeNode(id="solo", connections=[])}


# ---------------------------------------------------------------------------
# Hospital graph — anonymized, no PHI fields anywhere
# ---------------------------------------------------------------------------

@pytest.fixture
def hospital_graph():
    """
    Simplified hospital topology.
    Nodes: triage, bed_01..bed_04, icu_01, maintenance_01, radiology
    All IDs are role+number — zero PHI.
    """
    return {
        "triage":        TreeNode(id="triage",        connections=["bed_01", "bed_02", "bed_03", "radiology"]),
        "bed_01":        TreeNode(id="bed_01",         connections=["triage", "icu_01"]),
        "bed_02":        TreeNode(id="bed_02",         connections=["triage"]),
        "bed_03":        TreeNode(id="bed_03",         connections=["triage", "icu_01"]),
        "bed_04":        TreeNode(id="bed_04",         connections=["maintenance_01"]),  # only reachable via maintenance
        "icu_01":        TreeNode(id="icu_01",         connections=["bed_01", "bed_03"]),
        "maintenance_01":TreeNode(id="maintenance_01", connections=["bed_04"]),
        "radiology":     TreeNode(id="radiology",      connections=["triage"]),
    }


# ---------------------------------------------------------------------------
# Constraint profiles
# ---------------------------------------------------------------------------

@pytest.fixture
def standard_profile():
    """Balanced profile, no blocks."""
    return ConstraintProfile(
        profile_name="balanced_route",
        intent_summary="Route with equal priority across all dimensions.",
        weights={"time": 0.2, "cost": 0.2, "risk": 0.2, "reliability": 0.2, "distance": 0.2},
        constraints={"avoid": [], "prefer": [], "hard_block": []},
        notes="",
        raw_intent="balanced routing"
    )


@pytest.fixture
def hospital_profile():
    """
    Hospital routing: avoid maintenance, hard-block maintenance_01.
    Prefer bed_01 and bed_03 (standard care beds).
    """
    return ConstraintProfile(
        profile_name="hospital_triage_routing",
        intent_summary="Route patients from triage to nearest available bed, avoid maintenance areas.",
        weights={"time": 0.4, "cost": 0.1, "risk": 0.2, "reliability": 0.2, "distance": 0.1},
        constraints={
            "avoid":      ["radiology"],
            "prefer":     ["bed_01", "bed_03"],
            "hard_block": ["maintenance_01"],
        },
        notes="Never route through maintenance. ICU only if no standard bed available.",
        raw_intent="route patients from triage to nearest available bed, avoid maintenance rooms"
    )


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_log(tmp_path):
    """ActivityLog backed by a temp file — clean per test."""
    return ActivityLog(str(tmp_path / "test.log"))


# ---------------------------------------------------------------------------
# Mocked synthesizer for entry_point tests (no API key, no spend)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_synthesizer(standard_profile):
    """Returns a mock IntentWeightSynthesizer that always returns standard_profile."""
    synth = MagicMock()
    synth.synthesize.return_value = standard_profile
    return synth
