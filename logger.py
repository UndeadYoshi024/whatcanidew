"""
Activity Log — Tree Topology Heuristics
========================================
Append-only. Human legible. Never modified, only extended.
Every routing decision leaves a permanent, auditable record.

One line per decision. Format:
    [TIMESTAMP] | FROM: start | TO: target | DISTANCE: n | PATH: a -> b -> c | CALLER: system

Humans read this. LLMs do not. Feed data forward manually.

Usage:
    from logger import ActivityLog
    log = ActivityLog("routing_decisions.log")
    log.write(start="warehouse_a", target="port_b", distance=3, path=["warehouse_a","hub_1","port_b"], caller="invoice_router")
"""

from __future__ import annotations
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


class ActivityLog:

    def __init__(self, filepath: str = "routing_decisions.log") -> None:
        self.filepath = Path(filepath)
        self._ensure_exists()

    def _ensure_exists(self) -> None:
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(f"# Tree Topology Heuristics — Activity Log\n")
                f.write(f"# Created: {self._now()}\n")
                f.write(f"# Format: [TIMESTAMP] | FROM: x | TO: x | DISTANCE: n | PATH: a -> b -> c | CALLER: system\n")
                f.write(f"# This file is append-only. Do not edit. Do not delete entries.\n")
                f.write(f"# Feed data forward to other systems manually.\n\n")

    def write(
        self,
        start: str,
        target: str,
        distance: float,
        path: Optional[List[str]],
        caller: str = "unknown",
        note: str = ""
    ) -> None:
        timestamp = self._now()
        path_str = " -> ".join(path) if path else "UNREACHABLE"
        dist_str = str(distance) if distance >= 0 else "UNREACHABLE"
        line = f"[{timestamp}] | FROM: {start} | TO: {target} | DISTANCE: {dist_str} | PATH: {path_str} | CALLER: {caller}"
        if note:
            line += f" | NOTE: {note}"
        line += "\n"
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(line)

    def write_nearest(
        self,
        start: str,
        candidates: List[str],
        nearest: Optional[str],
        distance: float,
        path: Optional[List[str]],
        caller: str = "unknown",
        note: str = ""
    ) -> None:
        timestamp = self._now()
        candidates_str = ", ".join(candidates)
        path_str = " -> ".join(path) if path else "UNREACHABLE"
        dist_str = str(distance) if distance >= 0 else "UNREACHABLE"
        nearest_str = nearest if nearest else "NONE REACHABLE"
        line = (
            f"[{timestamp}] | NEAREST SEARCH | FROM: {start} | "
            f"CANDIDATES: [{candidates_str}] | NEAREST: {nearest_str} | "
            f"DISTANCE: {dist_str} | PATH: {path_str} | CALLER: {caller}"
        )
        if note:
            line += f" | NOTE: {note}"
        line += "\n"
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(line)

    def rotate(self, archive_suffix: Optional[str] = None) -> str:
        """
        Archive the current log and start a fresh one.
        Returns the path of the archived file.
        Human operator calls this manually — never automated.
        """
        suffix = archive_suffix or datetime.now(timezone.utc).strftime("%Y_%m_%d_%H%M%S")
        stem = self.filepath.stem
        ext = self.filepath.suffix
        archive_path = self.filepath.parent / f"{stem}_{suffix}{ext}"
        self.filepath.rename(archive_path)
        self._ensure_exists()
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(f"# Continued from archive: {archive_path.name}\n\n")
        return str(archive_path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
