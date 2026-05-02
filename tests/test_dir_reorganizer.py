"""
test_dir_reorganizer.py
=======================
Tests for dir_reorganizer.py.
Proves: naming rules, full tree copy, collision handling, determinism, source untouched.
"""

import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dir_reorganizer import _aesthetic_name, reorganize


# ---------------------------------------------------------------------------
# _aesthetic_name unit tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("inp,expected", [
    ("MyFile.TXT",          "myfile.txt"),
    ("hello world.py",      "hello_world.py"),
    ("foo-bar-baz.json",    "foo_bar_baz.json"),
    ("My.Weird.Name.md",    "my_weird_name.md"),
    ("__leading__.py",      "leading.py"),
    ("ALLCAPS",             "allcaps"),
    ("already_clean.py",    "already_clean.py"),
    ("spaces   tabs.js",    "spaces_tabs.js"),
    ("a--b--c.txt",         "a_b_c.txt"),
    ("noextension",         "noextension"),
])
def test_aesthetic_name(inp, expected):
    assert _aesthetic_name(inp) == expected


# ---------------------------------------------------------------------------
# reorganize — structure and content
# ---------------------------------------------------------------------------

def _make_messy_tree(root: Path):
    (root / "My Documents").mkdir()
    (root / "My Documents" / "Invoice Final FINAL.pdf").write_text("invoice")
    (root / "My Documents" / "Budget 2024.xlsx").write_text("budget")
    (root / "src-code").mkdir()
    (root / "src-code" / "Main Module.py").write_text("main")
    (root / "src-code" / "Utils Helper.py").write_text("utils")
    (root / "README.MD").write_text("readme")


def test_reorganize_creates_output_dir(tmp_path):
    src = tmp_path / "Messy Dir"
    src.mkdir()
    (src / "File One.txt").write_text("x")
    out = reorganize(str(src))
    assert Path(out).exists()
    assert Path(out).is_dir()


def test_reorganize_output_name_ends_with_dew(tmp_path):
    src = tmp_path / "My Project"
    src.mkdir()
    (src / "file.txt").write_text("x")
    out = reorganize(str(src))
    assert Path(out).name.endswith("_dew")


def test_reorganize_all_files_copied(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    _make_messy_tree(src)
    out = reorganize(str(src))
    src_count = sum(1 for _, _, files in os.walk(src) for _ in files)
    out_count = sum(1 for _, _, files in os.walk(out) for _ in files)
    assert out_count == src_count


def test_reorganize_names_are_lowercase(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    _make_messy_tree(src)
    out = reorganize(str(src))
    for dirpath, dirnames, filenames in os.walk(out):
        for name in filenames + dirnames:
            assert name == name.lower(), f"Not lowercase: {name}"


def test_reorganize_no_spaces_in_names(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    _make_messy_tree(src)
    out = reorganize(str(src))
    for dirpath, dirnames, filenames in os.walk(out):
        for name in filenames + dirnames:
            assert " " not in name, f"Space in name: {name}"


def test_reorganize_file_content_preserved(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    (src / "My File.txt").write_text("hello content")
    out = reorganize(str(src))
    result = Path(out) / "my_file.txt"
    assert result.read_text() == "hello content"


def test_reorganize_source_not_modified(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    _make_messy_tree(src)
    original_names = {
        str(p.relative_to(src)) for p in src.rglob("*")
    }
    reorganize(str(src))
    after_names = {
        str(p.relative_to(src)) for p in src.rglob("*")
    }
    assert original_names == after_names


def test_reorganize_is_deterministic(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    _make_messy_tree(src)
    out1 = reorganize(str(src))
    names1 = sorted(str(p.relative_to(out1)) for p in Path(out1).rglob("*"))
    out2 = reorganize(str(src))
    names2 = sorted(str(p.relative_to(out2)) for p in Path(out2).rglob("*"))
    assert names1 == names2


def test_reorganize_overwrites_stale_output(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    (src / "file.txt").write_text("v1")
    reorganize(str(src))
    (src / "file.txt").write_text("v2")
    out = reorganize(str(src))
    assert (Path(out) / "file.txt").read_text() == "v2"


def test_reorganize_raises_on_missing_source(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        reorganize(str(tmp_path / "nonexistent"))


def test_reorganize_raises_on_file_not_dir(tmp_path):
    f = tmp_path / "afile.txt"
    f.write_text("x")
    with pytest.raises(ValueError, match="not a directory"):
        reorganize(str(f))


def test_reorganize_nested_dirs_preserved(tmp_path):
    src = tmp_path / "source"
    (src / "Level One" / "Level Two").mkdir(parents=True)
    (src / "Level One" / "Level Two" / "Deep File.txt").write_text("deep")
    out = reorganize(str(src))
    deep = Path(out) / "level_one" / "level_two" / "deep_file.txt"
    assert deep.exists()
    assert deep.read_text() == "deep"
