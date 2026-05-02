"""
test_api.py
===========
Tests for docker/server.py via FastAPI TestClient.
No Docker, no network, no API key. Pure in-process.
Covers all endpoints: /health, /distance, /path, /nearest, /synthesize, /route.
"""

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Point imports at the test working dir
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "docker"))

os.environ.setdefault("DEW_LOG_PATH", "/tmp/dew_api_test.log")

from fastapi.testclient import TestClient
from intent_weight_synthesizer import ConstraintProfile
import dataclasses

BALANCED_PROFILE = ConstraintProfile(
    profile_name="balanced",
    intent_summary="Balanced routing.",
    weights={"time": 0.2, "cost": 0.2, "risk": 0.2, "reliability": 0.2, "distance": 0.2},
    constraints={"avoid": [], "prefer": [], "hard_block": []},
    notes="",
    raw_intent="balanced"
)

# Patch synthesizer before importing server (it instantiates at module level)
with patch("intent_weight_synthesizer.IntentWeightSynthesizer.synthesize",
           return_value=BALANCED_PROFILE):
    import server
    client = TestClient(server.app)


SIMPLE_GRAPH_PAYLOAD = {
    "a": {"connections": ["b"]},
    "b": {"connections": ["a", "c"]},
    "c": {"connections": ["b", "d"]},
    "d": {"connections": ["c"]},
}

WEIGHTED_GRAPH_PAYLOAD = {
    "a": {"connections": ["b", "c"], "weights": {"b": 1.0, "c": 5.0}},
    "b": {"connections": ["a", "d"], "weights": {"a": 1.0, "d": 1.0}},
    "c": {"connections": ["a", "d"], "weights": {"a": 5.0, "d": 1.0}},
    "d": {"connections": ["b", "c"], "weights": {"b": 1.0, "c": 1.0}},
}


class TestHealth:

    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_has_status_field(self):
        r = client.get("/health")
        assert "status" in r.json()

    def test_health_status_value(self):
        r = client.get("/health")
        assert r.json()["status"] == "dew-ing fine"


class TestDistanceEndpoint:

    def test_distance_returns_200(self):
        r = client.post("/distance", json={
            "graph": SIMPLE_GRAPH_PAYLOAD, "start": "a", "target": "d"
        })
        assert r.status_code == 200

    def test_distance_correct_value(self):
        r = client.post("/distance", json={
            "graph": SIMPLE_GRAPH_PAYLOAD, "start": "a", "target": "d"
        })
        assert r.json()["distance"] == 3

    def test_distance_same_node(self):
        r = client.post("/distance", json={
            "graph": SIMPLE_GRAPH_PAYLOAD, "start": "b", "target": "b"
        })
        assert r.json()["distance"] == 0

    def test_distance_unreachable(self):
        disconnected = {
            "a": {"connections": ["b"]}, "b": {"connections": ["a"]},
            "x": {"connections": ["y"]}, "y": {"connections": ["x"]},
        }
        r = client.post("/distance", json={
            "graph": disconnected, "start": "a", "target": "x"
        })
        assert r.json()["distance"] == -1

    def test_distance_weighted_graph(self):
        r = client.post("/distance", json={
            "graph": WEIGHTED_GRAPH_PAYLOAD, "start": "a", "target": "d"
        })
        assert r.json()["distance"] == pytest.approx(2.0)


class TestPathEndpoint:

    def test_path_returns_200(self):
        r = client.post("/path", json={
            "graph": SIMPLE_GRAPH_PAYLOAD, "start": "a", "target": "d"
        })
        assert r.status_code == 200

    def test_path_has_path_field(self):
        r = client.post("/path", json={
            "graph": SIMPLE_GRAPH_PAYLOAD, "start": "a", "target": "d"
        })
        assert "path" in r.json()

    def test_path_correct_sequence(self):
        r = client.post("/path", json={
            "graph": SIMPLE_GRAPH_PAYLOAD, "start": "a", "target": "d"
        })
        assert r.json()["path"] == ["a", "b", "c", "d"]

    def test_path_unreachable_returns_null(self):
        disconnected = {
            "a": {"connections": []}, "b": {"connections": []},
        }
        r = client.post("/path", json={
            "graph": disconnected, "start": "a", "target": "b"
        })
        assert r.json()["path"] is None
        assert r.json()["distance"] == -1

    def test_path_weighted_picks_cheaper(self):
        r = client.post("/path", json={
            "graph": WEIGHTED_GRAPH_PAYLOAD, "start": "a", "target": "d"
        })
        assert r.json()["path"] == ["a", "b", "d"]


class TestNearestEndpoint:

    def test_nearest_returns_200(self):
        r = client.post("/nearest", json={
            "graph": SIMPLE_GRAPH_PAYLOAD,
            "start": "a",
            "targets": ["c", "d"]
        })
        assert r.status_code == 200

    def test_nearest_finds_closer_target(self):
        r = client.post("/nearest", json={
            "graph": SIMPLE_GRAPH_PAYLOAD,
            "start": "a",
            "targets": ["b", "d"]
        })
        assert r.json()["target_id"] == "b"
        assert r.json()["distance"] == 1

    def test_nearest_no_reachable_targets(self):
        disconnected = {
            "a": {"connections": ["b"]}, "b": {"connections": ["a"]},
            "x": {"connections": []},
        }
        r = client.post("/nearest", json={
            "graph": disconnected,
            "start": "a",
            "targets": ["x"]
        })
        assert r.json()["target_id"] is None
        assert r.json()["distance"] == -1

    def test_nearest_has_path_field(self):
        r = client.post("/nearest", json={
            "graph": SIMPLE_GRAPH_PAYLOAD,
            "start": "a",
            "targets": ["b", "c"]
        })
        assert "path" in r.json()
        assert r.json()["path"] is not None


class TestSynthesizeEndpoint:

    def test_synthesize_returns_200(self):
        with patch.object(server._synthesizer, "synthesize", return_value=BALANCED_PROFILE):
            r = client.post("/synthesize", json={"intent": "route fast"})
        assert r.status_code == 200

    def test_synthesize_returns_profile_fields(self):
        with patch.object(server._synthesizer, "synthesize", return_value=BALANCED_PROFILE):
            r = client.post("/synthesize", json={"intent": "route fast"})
        data = r.json()
        assert "profile_name" in data
        assert "weights" in data
        assert "constraints" in data


class TestRouteEndpoint:

    def test_route_returns_200(self):
        with patch.object(server._synthesizer, "synthesize", return_value=BALANCED_PROFILE):
            with patch("entry_point.IntentWeightSynthesizer") as M:
                M.return_value.synthesize.return_value = BALANCED_PROFILE
                r = client.post("/route", json={
                    "intent": "balanced",
                    "graph": SIMPLE_GRAPH_PAYLOAD,
                    "start": "a",
                    "target": "d"
                })
        assert r.status_code == 200

    def test_route_has_distance_and_path(self):
        with patch("entry_point.IntentWeightSynthesizer") as M:
            M.return_value.synthesize.return_value = BALANCED_PROFILE
            r = client.post("/route", json={
                "intent": "balanced",
                "graph": SIMPLE_GRAPH_PAYLOAD,
                "start": "a",
                "target": "d"
            })
        data = r.json()
        assert "distance" in data
        assert "path" in data
