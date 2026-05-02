"""
test_entry_point.py
===================
Tests for entry_point.py.
Fully deterministic — no API key, no network. IntentWeightSynthesizer is mocked.
Tests cover: cache behavior, full pipeline, log output, unreachable paths.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import entry_point as ep
from entry_point import route
from intent_weight_synthesizer import ConstraintProfile


BALANCED_PROFILE = ConstraintProfile(
    profile_name="balanced",
    intent_summary="Balanced routing.",
    weights={"time": 0.2, "cost": 0.2, "risk": 0.2, "reliability": 0.2, "distance": 0.2},
    constraints={"avoid": [], "prefer": [], "hard_block": []},
    notes="",
    raw_intent="balanced"
)

BLOCK_B_PROFILE = ConstraintProfile(
    profile_name="block_b",
    intent_summary="Block node b.",
    weights={"time": 0.2, "cost": 0.2, "risk": 0.2, "reliability": 0.2, "distance": 0.2},
    constraints={"avoid": [], "prefer": [], "hard_block": ["b"]},
    notes="",
    raw_intent="block b"
)


@pytest.fixture(autouse=True)
def clear_profile_cache():
    """Reset the module-level cache before every test."""
    ep._profile_cache.clear()
    yield
    ep._profile_cache.clear()


class TestRoutePipeline:

    def test_route_returns_path_result(self, simple_graph, tmp_path):
        with patch("entry_point.IntentWeightSynthesizer") as MockSynth:
            MockSynth.return_value.synthesize.return_value = BALANCED_PROFILE
            result = route(
                user_intent="balanced",
                graph=simple_graph,
                start="a",
                target="d",
                log_path=str(tmp_path / "test.log"),
            )
        assert result.distance > 0
        assert result.path is not None
        assert result.path[0] == "a"
        assert result.path[-1] == "d"

    def test_route_writes_to_log(self, simple_graph, tmp_path):
        log_path = str(tmp_path / "route.log")
        with patch("entry_point.IntentWeightSynthesizer") as MockSynth:
            MockSynth.return_value.synthesize.return_value = BALANCED_PROFILE
            route(
                user_intent="balanced",
                graph=simple_graph,
                start="a",
                target="d",
                log_path=log_path,
            )
        content = Path(log_path).read_text()
        assert "FROM: a" in content
        assert "TO: d" in content

    def test_route_unreachable_logs_unreachable(self, disconnected_graph, tmp_path):
        log_path = str(tmp_path / "unreachable.log")
        with patch("entry_point.IntentWeightSynthesizer") as MockSynth:
            MockSynth.return_value.synthesize.return_value = BALANCED_PROFILE
            result = route(
                user_intent="balanced",
                graph=disconnected_graph,
                start="a",
                target="x",
                log_path=log_path,
            )
        assert result.distance == -1
        content = Path(log_path).read_text()
        assert "UNREACHABLE" in content

    def test_route_respects_hard_block(self, simple_graph, tmp_path):
        """Hard-blocking b makes d unreachable from a in the simple chain."""
        with patch("entry_point.IntentWeightSynthesizer") as MockSynth:
            MockSynth.return_value.synthesize.return_value = BLOCK_B_PROFILE
            result = route(
                user_intent="block b",
                graph=simple_graph,
                start="a",
                target="d",
                log_path=str(tmp_path / "block.log"),
            )
        assert result.distance == -1


class TestProfileCache:

    def test_same_intent_synthesizes_once(self, simple_graph, tmp_path):
        with patch("entry_point.IntentWeightSynthesizer") as MockSynth:
            instance = MockSynth.return_value
            instance.synthesize.return_value = BALANCED_PROFILE
            log_path = str(tmp_path / "cache.log")
            route("balanced", simple_graph, "a", "d", log_path)
            route("balanced", simple_graph, "a", "d", log_path)
            route("balanced", simple_graph, "a", "d", log_path)
        assert instance.synthesize.call_count == 1

    def test_different_intents_synthesize_each_time(self, simple_graph, tmp_path):
        with patch("entry_point.IntentWeightSynthesizer") as MockSynth:
            instance = MockSynth.return_value
            instance.synthesize.return_value = BALANCED_PROFILE
            log_path = str(tmp_path / "cache2.log")
            route("intent_one", simple_graph, "a", "d", log_path)
            route("intent_two", simple_graph, "a", "d", log_path)
        assert instance.synthesize.call_count == 2

    def test_cache_populated_after_first_call(self, simple_graph, tmp_path):
        with patch("entry_point.IntentWeightSynthesizer") as MockSynth:
            MockSynth.return_value.synthesize.return_value = BALANCED_PROFILE
            route("cache_test", simple_graph, "a", "d",
                  str(tmp_path / "c.log"))
        assert "cache_test" in ep._profile_cache

    def test_cache_cleared_between_tests(self):
        """autouse fixture must reset cache — verified here."""
        assert ep._profile_cache == {}
