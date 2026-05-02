from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from collections import deque
from typing import Dict, List

from tree_topology_heuristics import TreeNode


def copy_codebase(src: str, dst: str) -> None:
    if os.path.exists(dst):
        raise FileExistsError(f"Destination already exists: {dst}")
    shutil.copytree(src, dst)


def detect_erodable(path: str) -> List[str]:
    result = []
    for dirpath, _, filenames in os.walk(path):
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            stem = os.path.splitext(fname)[0]
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                for dec in node.decorator_list:
                    name = None
                    if isinstance(dec, ast.Name):
                        name = dec.id
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                        name = dec.func.id
                    if name in ("stateful", "non_deterministic", "ttl"):
                        result.append(f"{stem}.{node.name}")
                        break
    return sorted(result)


def _collect_py_files(path: str) -> List[tuple]:
    files = []
    for dirpath, _, filenames in os.walk(path):
        for fname in filenames:
            if fname.endswith(".py"):
                stem = os.path.splitext(fname)[0]
                files.append((os.path.join(dirpath, fname), stem))
    return files


def build_call_graph(path: str) -> Dict[str, TreeNode]:
    py_files = _collect_py_files(path)
    if not py_files:
        return {}

    parsed = []
    for fpath, stem in py_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
        except SyntaxError:
            continue
        parsed.append((fpath, stem, tree))

    if not parsed:
        return {}

    func_defs: Dict[str, tuple] = {}
    for fpath, stem, tree in parsed:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                nid = f"{stem}.{node.name}"
                func_defs[nid] = (stem, node.name, node)

    if not func_defs:
        return {}

    bare_to_nids: Dict[str, List[str]] = {}
    for nid, (stem, fname, _) in func_defs.items():
        bare_to_nids.setdefault(fname, []).append(nid)

    graph: Dict[str, TreeNode] = {}
    for nid, (stem, fname, funcnode) in func_defs.items():
        connections: List[str] = []
        weights: Dict[str, float] = {}
        for node in ast.walk(funcnode):
            if not isinstance(node, ast.Call):
                continue
            called_name = None
            if isinstance(node.func, ast.Name):
                called_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                called_name = node.func.attr
            if called_name and called_name in bare_to_nids:
                for target_nid in bare_to_nids[called_name]:
                    if target_nid != nid and target_nid not in weights:
                        connections.append(target_nid)
                        weights[target_nid] = 1.0
        graph[nid] = TreeNode(id=nid, connections=connections, weights=weights)

    erodable = detect_erodable(path)
    for nid in erodable:
        if nid in graph:
            for k in list(graph[nid].weights.keys()):
                graph[nid].weights[k] = float("inf")

    return graph


def apply_dewdrop(graph: Dict[str, TreeNode], instruction: dict, path: str) -> None:
    old = instruction["old"]
    new = instruction["new"]

    if not os.path.isabs(path) or not os.path.isdir(path):
        raise ValueError(f"apply_dewdrop: path must be an absolute path to an existing directory: {path!r}")

    if old in graph and graph[old].weights and all(
        w == float("inf") for w in graph[old].weights.values()
    ):
        return

    py_files = _collect_py_files(path)
    root = os.path.realpath(path)
    snapshot: Dict[str, str] = {}
    for fpath, _ in py_files:
        rel = os.path.relpath(fpath, path)
        if not os.path.realpath(fpath).startswith(root + os.sep):
            raise ValueError(f"Path traversal detected: {fpath!r}")
        with open(fpath, "r", encoding="utf-8") as f:
            snapshot[rel] = f.read()

    for fpath, _ in py_files:
        rel = os.path.relpath(fpath, path)
        if not os.path.realpath(fpath).startswith(root + os.sep):
            raise ValueError(f"Path traversal detected: {fpath!r}")
        content = re.sub(r'\b' + re.escape(old) + r'\b', new, snapshot[rel])
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

    result = subprocess.run([sys.executable, "-m", "pytest", path], capture_output=True)

    if result.returncode != 0:
        for rel, content in snapshot.items():
            fpath = os.path.join(path, rel)
            if not os.path.realpath(fpath).startswith(root + os.sep):
                raise ValueError(f"Path traversal detected: {fpath!r}")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)


def chase_ripples(graph: Dict[str, TreeNode], node_id: str) -> List[str]:
    if node_id not in graph:
        return []

    visited = {node_id}
    queue = deque([node_id])
    reachable: List[str] = []

    while queue:
        current = queue.popleft()
        current_node = graph.get(current)
        if not current_node:
            continue
        for conn in current_node.connections:
            if conn not in visited:
                visited.add(conn)
                reachable.append(conn)
                queue.append(conn)

    return reachable


def generate_report(path: str, dewdrops: list, flags: list, erodable: list) -> None:
    report = {
        "schema_version": "1.0",
        "dewdrops": dewdrops,
        "flags": flags,
        "erodable": erodable,
    }
    with open(os.path.join(path, "ripple_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def run(src: str, config: dict) -> None:
    output_dir = config["output_dir"]

    if os.path.exists(output_dir):
        raise FileExistsError(f"Output directory already exists: {output_dir}")

    has_tests = False
    try:
        for fname in os.listdir(src):
            if fname.startswith("test_") and fname.endswith(".py"):
                has_tests = True
                break
            if fname == "tests" and os.path.isdir(os.path.join(src, fname)):
                has_tests = True
                break
    except OSError:
        pass

    if not has_tests:
        input("No test suite found in source. Continue? ")

    copy_codebase(src, output_dir)
    erodable = detect_erodable(src)
    graph = build_call_graph(src)

    for instruction in config.get("dewdrops", []):
        apply_dewdrop(graph, instruction, output_dir)

    flags: list = []
    generate_report(output_dir, config.get("dewdrops", []), flags, erodable)
