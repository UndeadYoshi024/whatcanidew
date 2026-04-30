from __future__ import annotations

from typing import Dict, Optional

from tree_topology_heuristics import TreeTopologyHeuristics, TreeNode, PathResult
from intent_weight_synthesizer import IntentWeightSynthesizer, ConstraintProfile
from graph_weight_mapper import apply_weights
from logger import ActivityLog

_profile_cache: Dict[str, ConstraintProfile] = {}


def route(
    user_intent: str,
    graph: Dict[str, TreeNode],
    start: str,
    target: str,
    api_key: str,
    log_path: str = "logs/routing_decisions.log",
    model: str = "claude-haiku-4-5-20251001",
) -> PathResult:
    log = ActivityLog(log_path)

    if user_intent in _profile_cache:
        profile = _profile_cache[user_intent]
    else:
        synthesizer = IntentWeightSynthesizer(api_key=api_key, log=log, model=model)
        profile = synthesizer.synthesize(user_intent, caller="entry_point")
        _profile_cache[user_intent] = profile

    weighted_graph = apply_weights(graph, profile)
    result = TreeTopologyHeuristics.find_path(weighted_graph, start, target)
    log.write(start=start, target=target, distance=result.distance, path=result.path, caller="entry_point")

    return result
