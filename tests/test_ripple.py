"""
test_ripple.py
==============
Tests for ripple.py (pypi/ripple.py).
Covers copy_codebase, detect_erodable, build_call_graph, apply_dewdrop,
chase_ripples, generate_report, and run.
"""

import json
import os
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pypi"))

from tree_topology_heuristics import TreeNode
from ripple import (
    copy_codebase, detect_erodable, build_call_graph,
    apply_dewdrop, chase_ripples, generate_report, run,
)


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

def _make_simple_codebase(root: Path):
    (root / "pkg").mkdir()
    (root / "pkg" / "module.py").write_text("def hello(): pass\n")
    (root / "main.py").write_text("from pkg.module import hello\n")
    (root / "sub").mkdir()
    (root / "sub" / "util.py").write_text("X = 1\n")


def _make_erodable_codebase(root: Path):
    (root / "stateful_mod.py").write_text(textwrap.dedent("""\
        @stateful
        def persist_state(data):
            pass
    """))
    (root / "nondeterministic_mod.py").write_text(textwrap.dedent("""\
        @non_deterministic
        def fetch_random_value():
            pass
    """))
    (root / "ttl_mod.py").write_text(textwrap.dedent("""\
        @ttl(300)
        def get_cached_result():
            pass
    """))


def _make_rename_codebase(root: Path):
    (root / "definitions.py").write_text(textwrap.dedent("""\
        def old_func(x):
            return x + 1
    """))
    (root / "callers.py").write_text(textwrap.dedent("""\
        from definitions import old_func

        def run():
            return old_func(42)
    """))


def _make_erode_codebase(root: Path):
    (root / "erosion.py").write_text(textwrap.dedent("""\
        def erode(data):
            return data
    """))
    (root / "client.py").write_text(textwrap.dedent("""\
        from erosion import erode

        def process():
            return erode({})
    """))


def _directed_graph():
    # a → b → d
    # a → c
    # c and d have no outgoing edges
    return {
        "a": TreeNode(id="a", connections=["b", "c"]),
        "b": TreeNode(id="b", connections=["d"]),
        "c": TreeNode(id="c", connections=[]),
        "d": TreeNode(id="d", connections=[]),
    }


def _erodable_graph():
    # "erode" has all outgoing weights set to inf — it is an erodable surface
    return {
        "erode": TreeNode(
            id="erode",
            connections=["downstream"],
            weights={"downstream": float("inf")},
        ),
        "downstream": TreeNode(id="downstream", connections=[]),
        "normal": TreeNode(
            id="normal",
            connections=["downstream"],
            weights={"downstream": 1.0},
        ),
    }


def _rename_graph():
    return {
        "old_func": TreeNode(id="old_func", connections=["run"], weights={"run": 1.0}),
        "run": TreeNode(id="run", connections=[], weights={}),
    }


# ---------------------------------------------------------------------------
# copy_codebase
# ---------------------------------------------------------------------------

def test_copy_codebase_copies_all_files(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_simple_codebase(src)
    dst = tmp_path / "dst"
    copy_codebase(str(src), str(dst))
    src_count = sum(1 for p in src.rglob("*") if p.is_file())
    dst_count = sum(1 for p in dst.rglob("*") if p.is_file())
    assert dst_count == src_count


def test_copy_codebase_preserves_nested_structure(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_simple_codebase(src)
    dst = tmp_path / "dst"
    copy_codebase(str(src), str(dst))
    assert (dst / "pkg" / "module.py").exists()
    assert (dst / "sub" / "util.py").exists()


def test_copy_codebase_preserves_file_contents(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "sample.py").write_text("hello = 42\n")
    dst = tmp_path / "dst"
    copy_codebase(str(src), str(dst))
    assert (dst / "sample.py").read_text() == "hello = 42\n"


def test_copy_codebase_raises_if_dst_exists(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "x.py").write_text("x = 1\n")
    dst = tmp_path / "dst"
    dst.mkdir()
    with pytest.raises(FileExistsError):
        copy_codebase(str(src), str(dst))


# ---------------------------------------------------------------------------
# detect_erodable
# ---------------------------------------------------------------------------

def test_detect_erodable_returns_list(tmp_path):
    _make_erodable_codebase(tmp_path)
    assert isinstance(detect_erodable(str(tmp_path)), list)


def test_detect_erodable_all_items_are_strings(tmp_path):
    _make_erodable_codebase(tmp_path)
    for name in detect_erodable(str(tmp_path)):
        assert isinstance(name, str)


def test_detect_erodable_stateful_surface_present(tmp_path):
    _make_erodable_codebase(tmp_path)
    result = detect_erodable(str(tmp_path))
    assert any("persist_state" in name for name in result)


def test_detect_erodable_nondeterministic_surface_present(tmp_path):
    _make_erodable_codebase(tmp_path)
    result = detect_erodable(str(tmp_path))
    assert any("fetch_random_value" in name for name in result)


def test_detect_erodable_ttl_surface_present(tmp_path):
    _make_erodable_codebase(tmp_path)
    result = detect_erodable(str(tmp_path))
    assert any("get_cached_result" in name for name in result)


# ---------------------------------------------------------------------------
# build_call_graph + erodable surface edge cost
# ---------------------------------------------------------------------------

def test_build_call_graph_returns_dict(tmp_path):
    _make_simple_codebase(tmp_path)
    assert isinstance(build_call_graph(str(tmp_path)), dict)


def test_build_call_graph_values_are_tree_nodes(tmp_path):
    _make_simple_codebase(tmp_path)
    for node in build_call_graph(str(tmp_path)).values():
        assert isinstance(node, TreeNode)


def test_build_call_graph_node_ids_match_keys(tmp_path):
    _make_simple_codebase(tmp_path)
    graph = build_call_graph(str(tmp_path))
    for key, node in graph.items():
        assert node.id == key


def test_build_call_graph_erodable_nodes_have_inf_outgoing_weights(tmp_path):
    _make_erodable_codebase(tmp_path)
    erodable = detect_erodable(str(tmp_path))
    graph = build_call_graph(str(tmp_path))
    erodable_nodes = [node for nid, node in graph.items() if nid in erodable]
    assert erodable_nodes, "Erodable qualified names must appear as node ids in the graph"
    for node in erodable_nodes:
        for weight in node.weights.values():
            assert weight == float("inf")


# ---------------------------------------------------------------------------
# apply_dewdrop
# ---------------------------------------------------------------------------

def test_apply_dewdrop_renames_symbol_in_definition(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_rename_codebase(src)
    copy_path = tmp_path / "copy"
    copy_codebase(str(src), str(copy_path))
    instruction = {"action": "rename", "old": "old_func", "new": "new_func"}
    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0)
        apply_dewdrop(_rename_graph(), instruction, str(copy_path))
    text = (copy_path / "definitions.py").read_text()
    assert "new_func" in text
    assert "old_func" not in text


def test_apply_dewdrop_updates_call_sites(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_rename_codebase(src)
    copy_path = tmp_path / "copy"
    copy_codebase(str(src), str(copy_path))
    instruction = {"action": "rename", "old": "old_func", "new": "new_func"}
    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0)
        apply_dewdrop(_rename_graph(), instruction, str(copy_path))
    text = (copy_path / "callers.py").read_text()
    assert "new_func" in text
    assert "old_func" not in text


def test_apply_dewdrop_reverts_on_test_failure(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_rename_codebase(src)
    copy_path = tmp_path / "copy"
    copy_codebase(str(src), str(copy_path))
    snapshot = {p.relative_to(copy_path): p.read_text() for p in copy_path.rglob("*.py")}
    instruction = {"action": "rename", "old": "old_func", "new": "new_func"}
    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=1)
        apply_dewdrop(_rename_graph(), instruction, str(copy_path))
    for rel, original in snapshot.items():
        assert (copy_path / rel).read_text() == original


def test_apply_dewdrop_skips_erodable_node(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_erode_codebase(src)
    copy_path = tmp_path / "copy"
    copy_codebase(str(src), str(copy_path))
    snapshot = {p.relative_to(copy_path): p.read_text() for p in copy_path.rglob("*.py")}
    instruction = {"action": "rename", "old": "erode", "new": "erode_renamed"}
    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0)
        apply_dewdrop(_erodable_graph(), instruction, str(copy_path))
    for rel, original in snapshot.items():
        assert (copy_path / rel).read_text() == original


# ---------------------------------------------------------------------------
# chase_ripples
# ---------------------------------------------------------------------------

def test_chase_ripples_returns_list():
    assert isinstance(chase_ripples(_directed_graph(), "a"), list)


def test_chase_ripples_all_downstream_reachable():
    assert set(chase_ripples(_directed_graph(), "a")) == {"b", "c", "d"}


def test_chase_ripples_excludes_origin_node():
    assert "a" not in chase_ripples(_directed_graph(), "a")


def test_chase_ripples_single_hop():
    assert set(chase_ripples(_directed_graph(), "b")) == {"d"}


def test_chase_ripples_empty_when_no_outgoing_connections():
    assert chase_ripples(_directed_graph(), "c") == []


def test_chase_ripples_empty_for_leaf_node():
    assert chase_ripples(_directed_graph(), "d") == []


def test_chase_ripples_node_ids_are_strings():
    for nid in chase_ripples(_directed_graph(), "a"):
        assert isinstance(nid, str)


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------

def test_generate_report_creates_json_file(tmp_path):
    generate_report(str(tmp_path), [], [], [])
    assert (tmp_path / "ripple_report.json").exists()


def test_generate_report_is_valid_json(tmp_path):
    generate_report(str(tmp_path), [], [], [])
    json.loads((tmp_path / "ripple_report.json").read_text())


def test_generate_report_has_schema_version(tmp_path):
    generate_report(str(tmp_path), [], [], [])
    data = json.loads((tmp_path / "ripple_report.json").read_text())
    assert "schema_version" in data


def test_generate_report_schema_version_is_string(tmp_path):
    generate_report(str(tmp_path), [], [], [])
    data = json.loads((tmp_path / "ripple_report.json").read_text())
    assert isinstance(data["schema_version"], str)


def test_generate_report_has_dewdrops_key(tmp_path):
    generate_report(str(tmp_path), [], [], [])
    assert "dewdrops" in json.loads((tmp_path / "ripple_report.json").read_text())


def test_generate_report_has_flags_key(tmp_path):
    generate_report(str(tmp_path), [], [], [])
    assert "flags" in json.loads((tmp_path / "ripple_report.json").read_text())


def test_generate_report_has_erodable_key(tmp_path):
    generate_report(str(tmp_path), [], [], [])
    assert "erodable" in json.loads((tmp_path / "ripple_report.json").read_text())


def test_generate_report_dewdrops_matches_input(tmp_path):
    dewdrops = [{"action": "rename", "old": "foo", "new": "bar"}]
    generate_report(str(tmp_path), dewdrops, [], [])
    data = json.loads((tmp_path / "ripple_report.json").read_text())
    assert data["dewdrops"] == dewdrops


def test_generate_report_flags_matches_input(tmp_path):
    flags = ["potential breakage in module.py"]
    generate_report(str(tmp_path), [], flags, [])
    data = json.loads((tmp_path / "ripple_report.json").read_text())
    assert data["flags"] == flags


def test_generate_report_erodable_matches_input(tmp_path):
    erodable = ["stateful_mod.persist_state", "ttl_mod.get_cached_result"]
    generate_report(str(tmp_path), [], [], erodable)
    data = json.loads((tmp_path / "ripple_report.json").read_text())
    assert data["erodable"] == erodable


# ---------------------------------------------------------------------------
# build_call_graph — negative paths
# ---------------------------------------------------------------------------

def test_build_call_graph_empty_directory(tmp_path):
    assert build_call_graph(str(tmp_path)) == {}


def test_build_call_graph_no_python_files(tmp_path):
    (tmp_path / "readme.txt").write_text("nothing here\n")
    assert build_call_graph(str(tmp_path)) == {}


def test_build_call_graph_syntax_error_file_does_not_raise(tmp_path):
    (tmp_path / "broken.py").write_text("def oops(:\n    pass\n")
    result = build_call_graph(str(tmp_path))
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def test_run_raises_if_output_dir_exists(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "module.py").write_text("def func(): pass\n")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    with pytest.raises(FileExistsError):
        run(str(src), {"output_dir": str(output_dir)})


def test_run_calls_input_when_no_test_suite(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "module.py").write_text("def func(): pass\n")
    output_dir = tmp_path / "output"
    with patch("ripple.input", return_value="y") as mock_input:
        run(str(src), {"output_dir": str(output_dir)})
    mock_input.assert_called()


def test_run_is_deterministic(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "module.py").write_text("def func(): pass\n")
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    with patch("ripple.input", return_value="y"):
        run(str(src), {"output_dir": str(out1)})
        run(str(src), {"output_dir": str(out2)})
    r1 = json.loads((out1 / "ripple_report.json").read_text())
    r2 = json.loads((out2 / "ripple_report.json").read_text())
    assert r1["dewdrops"] == r2["dewdrops"]
    assert r1["flags"] == r2["flags"]
    assert r1["erodable"] == r2["erodable"]
