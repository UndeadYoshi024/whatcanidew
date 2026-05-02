from __future__ import annotations

import json
import os
from collections import deque
from typing import Dict, List, Optional

from tree_topology_heuristics import TreeNode
from logger import ActivityLog
from graph_weight_mapper import apply_weights
from intent_weight_synthesizer import ConstraintProfile


def build_graph(data: dict) -> Dict[str, TreeNode]:
    keys = set(data.keys())
    graph: Dict[str, TreeNode] = {}

    for key, value in data.items():
        connections: List[str] = []
        weights: Dict[str, float] = {}

        if isinstance(value, str):
            if value in keys and value != key:
                connections.append(value)
                weights[value] = 1.0
        elif isinstance(value, list):
            for element in value:
                if isinstance(element, str) and element in keys and element != key:
                    if element not in weights:
                        connections.append(element)
                        weights[element] = 1.0

        graph[key] = TreeNode(id=key, connections=connections, weights=weights)

    return graph


def find_disconnected(graph: Dict[str, TreeNode]) -> List[List[str]]:
    visited: set = set()
    components: List[List[str]] = []

    for node_id in graph:
        if node_id in visited:
            continue
        component: List[str] = []
        queue: deque = deque([node_id])
        visited.add(node_id)
        while queue:
            current = queue.popleft()
            component.append(current)
            node = graph.get(current)
            if node:
                for neighbor in node.connections:
                    if neighbor not in visited and neighbor in graph:
                        visited.add(neighbor)
                        queue.append(neighbor)
        components.append(component)

    if len(components) <= 1:
        return []

    components.sort(key=len, reverse=True)
    return components


def merge(base: Dict[str, TreeNode], extra: Dict[str, TreeNode]) -> Dict[str, TreeNode]:
    result: Dict[str, TreeNode] = {}
    all_keys = set(base.keys()) | set(extra.keys())

    for key in all_keys:
        base_node = base.get(key)
        extra_node = extra.get(key)

        if base_node is not None and extra_node is None:
            result[key] = TreeNode(
                id=key,
                connections=list(base_node.connections),
                weights=dict(base_node.weights),
            )
        elif base_node is None and extra_node is not None:
            result[key] = TreeNode(
                id=key,
                connections=list(extra_node.connections),
                weights=dict(extra_node.weights),
            )
        else:
            merged_connections: List[str] = list(base_node.connections)
            merged_weights: Dict[str, float] = dict(base_node.weights)
            for c in extra_node.connections:
                if c not in merged_weights:
                    merged_connections.append(c)
                    merged_weights[c] = 1.0
            result[key] = TreeNode(
                id=key,
                connections=merged_connections,
                weights=merged_weights,
            )

    return result


def load(path: str) -> Dict[str, TreeNode]:
    log = ActivityLog(os.environ.get("DEW_LOG_PATH", "routing_decisions.log"))

    abs_path = os.path.abspath(path)
    incorporated: set = set()

    if os.path.isdir(abs_path):
        root_dir = abs_path
        graph: Dict[str, TreeNode] = {}
        for dirpath, _dirnames, filenames in os.walk(abs_path):
            for filename in filenames:
                if not filename.endswith(".json") or filename == "dew.config.json":
                    continue
                abs_file = os.path.abspath(os.path.join(dirpath, filename))
                try:
                    with open(abs_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError):
                    continue
                graph = merge(graph, build_graph(data))
                incorporated.add(abs_file)
                log.write(
                    start=abs_file,
                    target=abs_file,
                    distance=-1,
                    path=None,
                    caller="repoe_adapter",
                    note=filename,
                )
    else:
        root_dir = os.path.dirname(abs_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        graph = build_graph(data)
        incorporated.add(abs_path)
        log.write(
            start=abs_path,
            target=abs_path,
            distance=-1,
            path=None,
            caller="repoe_adapter",
            note=f"loaded graph from {abs_path}",
        )

    config_path = os.path.join(root_dir, "dew.config.json")
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        raw_weights = config.get(
            "weights",
            {"time": 0.2, "cost": 0.2, "risk": 0.2, "reliability": 0.2, "distance": 0.2},
        )
        total = sum(raw_weights.values())
        normalized_weights = (
            {k: v / total for k, v in raw_weights.items()}
            if total > 0
            else {k: 1.0 / len(raw_weights) for k in raw_weights}
        )

        profile = ConstraintProfile(
            profile_name="dew_config",
            intent_summary="loaded from dew.config.json",
            weights=normalized_weights,
            constraints={
                "hard_block": config.get("hard_block", []),
                "prefer": config.get("prefer", []),
                "avoid": config.get("avoid", []),
            },
            notes="",
            raw_intent="",
        )
        graph = apply_weights(graph, profile)
        log.write(
            start=config_path,
            target=config_path,
            distance=-1,
            path=None,
            caller="repoe_adapter",
            note="applied dew.config.json",
        )

    while True:
        disconnected = find_disconnected(graph)
        if not disconnected:
            break

        disconnected_ids = {node_id for component in disconnected for node_id in component}

        candidates: List[str] = []
        for filename in os.listdir(root_dir):
            if not filename.endswith(".json") or filename == "dew.config.json":
                continue
            abs_candidate = os.path.abspath(os.path.join(root_dir, filename))
            if abs_candidate in incorporated:
                continue
            try:
                with open(abs_candidate, "r", encoding="utf-8") as f:
                    candidate_data = json.load(f)
                if any(node_id in candidate_data for node_id in disconnected_ids):
                    candidates.append(abs_candidate)
            except (json.JSONDecodeError, OSError):
                continue

        if candidates:
            print(f"Disconnected components detected: {[sorted(c) for c in disconnected]}")
            print(f"Candidate files found: {candidates}")
            answer = input("Merge candidate(s)? (y/n): ").strip().lower()
            if answer != "y":
                break
            for cand in candidates:
                with open(cand, "r", encoding="utf-8") as f:
                    extra_data = json.load(f)
                extra_graph = build_graph(extra_data)
                graph = merge(graph, extra_graph)
                incorporated.add(cand)
                log.write(
                    start=cand,
                    target=cand,
                    distance=-1,
                    path=None,
                    caller="repoe_adapter",
                    note=f"merged candidates from {cand}",
                )
        else:
            print("Disconnected components detected. No candidate files found.")
            user_path = input("Enter file path to merge (or Enter to skip): ").strip()
            if not user_path:
                break
            try:
                with open(user_path, "r", encoding="utf-8") as f:
                    extra_data = json.load(f)
                extra_graph = build_graph(extra_data)
                graph = merge(graph, extra_graph)
                incorporated.add(os.path.abspath(user_path))
                log.write(
                    start=user_path,
                    target=user_path,
                    distance=-1,
                    path=None,
                    caller="repoe_adapter",
                    note=f"merged candidates from {user_path}",
                )
            except (json.JSONDecodeError, OSError) as e:
                print(f"Error loading file: {e}")
                break

    return graph
