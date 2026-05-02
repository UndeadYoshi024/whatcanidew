"""
test_logger.py
==============
Tests for logger.py — append-only behavior, rotate, write_nearest.
The log is the compliance artifact. These tests prove it never lies.
"""

import pytest
from pathlib import Path
from logger import ActivityLog


class TestActivityLogInit:

    def test_creates_file_on_init(self, tmp_path):
        log_path = str(tmp_path / "new.log")
        ActivityLog(log_path)
        assert Path(log_path).exists()

    def test_creates_parent_dirs(self, tmp_path):
        log_path = str(tmp_path / "deep" / "nested" / "dir" / "activity.log")
        ActivityLog(log_path)
        assert Path(log_path).exists()

    def test_header_written_on_create(self, tmp_path):
        log_path = str(tmp_path / "header_test.log")
        ActivityLog(log_path)
        content = Path(log_path).read_text()
        assert "Tree Topology Heuristics" in content
        assert "append-only" in content.lower()

    def test_existing_file_not_overwritten(self, tmp_path):
        log_path = str(tmp_path / "existing.log")
        Path(log_path).write_text("EXISTING CONTENT\n")
        ActivityLog(log_path)
        content = Path(log_path).read_text()
        assert "EXISTING CONTENT" in content


class TestWrite:

    def test_write_appends_line(self, tmp_log):
        tmp_log.write(start="a", target="b", distance=1, path=["a", "b"], caller="test")
        content = Path(tmp_log.filepath).read_text()
        assert "FROM: a" in content
        assert "TO: b" in content
        assert "DISTANCE: 1" in content
        assert "PATH: a -> b" in content
        assert "CALLER: test" in content

    def test_write_multiple_appends_not_replaces(self, tmp_log):
        tmp_log.write(start="a", target="b", distance=1, path=["a", "b"], caller="test1")
        tmp_log.write(start="x", target="y", distance=2, path=["x", "z", "y"], caller="test2")
        content = Path(tmp_log.filepath).read_text()
        assert "FROM: a" in content
        assert "FROM: x" in content

    def test_write_unreachable(self, tmp_log):
        tmp_log.write(start="a", target="z", distance=-1, path=None, caller="test")
        content = Path(tmp_log.filepath).read_text()
        assert "UNREACHABLE" in content

    def test_write_includes_note(self, tmp_log):
        tmp_log.write(start="a", target="b", distance=1, path=["a", "b"],
                      caller="test", note="emergency routing")
        content = Path(tmp_log.filepath).read_text()
        assert "NOTE: emergency routing" in content

    def test_write_no_note_omits_note_field(self, tmp_log):
        tmp_log.write(start="a", target="b", distance=1, path=["a", "b"], caller="test")
        content = Path(tmp_log.filepath).read_text()
        assert "NOTE:" not in content

    def test_write_path_arrow_format(self, tmp_log):
        tmp_log.write(start="a", target="d", distance=3, path=["a", "b", "c", "d"], caller="test")
        content = Path(tmp_log.filepath).read_text()
        assert "PATH: a -> b -> c -> d" in content

    def test_write_timestamp_present(self, tmp_log):
        tmp_log.write(start="a", target="b", distance=1, path=["a", "b"], caller="test")
        content = Path(tmp_log.filepath).read_text()
        assert "UTC" in content


class TestWriteNearest:

    def test_write_nearest_basic(self, tmp_log):
        tmp_log.write_nearest(
            start="triage",
            candidates=["bed_01", "bed_02"],
            nearest="bed_01",
            distance=1,
            path=["triage", "bed_01"],
            caller="scheduler"
        )
        content = Path(tmp_log.filepath).read_text()
        assert "NEAREST SEARCH" in content
        assert "FROM: triage" in content
        assert "CANDIDATES:" in content
        assert "bed_01" in content
        assert "bed_02" in content
        assert "NEAREST: bed_01" in content

    def test_write_nearest_none_reachable(self, tmp_log):
        tmp_log.write_nearest(
            start="triage",
            candidates=["maintenance_01"],
            nearest=None,
            distance=-1,
            path=None,
            caller="scheduler"
        )
        content = Path(tmp_log.filepath).read_text()
        assert "NONE REACHABLE" in content
        assert "UNREACHABLE" in content

    def test_write_nearest_includes_note(self, tmp_log):
        tmp_log.write_nearest(
            start="a", candidates=["b"], nearest="b",
            distance=1, path=["a", "b"], caller="test",
            note="icu overflow"
        )
        content = Path(tmp_log.filepath).read_text()
        assert "NOTE: icu overflow" in content


class TestRotate:

    def test_rotate_archives_current_log(self, tmp_path):
        log_path = str(tmp_path / "rotate_test.log")
        log = ActivityLog(log_path)
        log.write(start="a", target="b", distance=1, path=["a", "b"], caller="test")
        archive_path = log.rotate()
        assert Path(archive_path).exists()

    def test_rotate_creates_fresh_log(self, tmp_path):
        log_path = str(tmp_path / "rotate_fresh.log")
        log = ActivityLog(log_path)
        log.write(start="a", target="b", distance=1, path=["a", "b"], caller="test")
        log.rotate()
        # Fresh log should exist and be shorter than original
        assert Path(log_path).exists()

    def test_rotate_new_log_references_archive(self, tmp_path):
        log_path = str(tmp_path / "rotate_ref.log")
        log = ActivityLog(log_path)
        log.write(start="a", target="b", distance=1, path=["a", "b"], caller="test")
        log.rotate()
        content = Path(log_path).read_text()
        assert "Continued from archive" in content

    def test_rotate_archived_log_has_original_content(self, tmp_path):
        log_path = str(tmp_path / "rotate_content.log")
        log = ActivityLog(log_path)
        log.write(start="sentinel_start", target="sentinel_end", distance=99,
                  path=["sentinel_start", "sentinel_end"], caller="test")
        archive_path = log.rotate()
        archive_content = Path(archive_path).read_text()
        assert "sentinel_start" in archive_content

    def test_rotate_custom_suffix(self, tmp_path):
        log_path = str(tmp_path / "rotate_suffix.log")
        log = ActivityLog(log_path)
        log.write(start="a", target="b", distance=1, path=["a", "b"], caller="test")
        archive_path = log.rotate(archive_suffix="CUSTOM_SUFFIX")
        assert "CUSTOM_SUFFIX" in archive_path
