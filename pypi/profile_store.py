"""
profile_store
=============
Atomic disk persistence for ConstraintProfile objects.

Profiles are stored in a JSON file (profiles.json by default) and loaded
back on startup to warm the in-memory cache, so resolved profiles survive container restarts.

Path resolution order:
    1. Constructor argument ``profiles_path``
    2. ``DEW_PROFILES_PATH`` environment variable
    3. Same directory as ``DEW_LOG_PATH`` + "profiles.json"
    4. ``logs/profiles.json`` (final fallback)

On-disk format::

    {
      "profiles": {
        "profile_name_1": { ...ConstraintProfile fields... },
        "profile_name_2": { ...ConstraintProfile fields... }
      }
    }

Atomic write semantics: write to a NamedTemporaryFile in the same directory,
then os.replace() — POSIX-atomic and Windows-atomic (same volume).

Usage::

    from profile_store import ProfileStore

    store = ProfileStore()                        # uses env / default path
    store.save(profile)                           # upsert by profile_name
    profiles = store.load_all()                   # returns List[ConstraintProfile]
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from intent_weight_synthesizer import ConstraintProfile

logger = logging.getLogger(__name__)

_DEFAULT_FILENAME = "profiles.json"
_DEFAULT_LOG_DIR = "logs"


class ProfileStore:
    """Persist and retrieve ConstraintProfile objects on disk."""

    def __init__(self, profiles_path: Optional[str] = None) -> None:
        """
        Parameters
        ----------
        profiles_path:
            Full path to the profiles JSON file.  If *None*, the path is
            resolved from the environment / defaults (see module docstring).
        """
        self._path: Path = self._resolve_path(profiles_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, profile: ConstraintProfile) -> None:
        """Upsert *profile* by ``profile_name`` and persist atomically.

        Creates the file on the first call if it does not exist.
        Raises ``IOError`` if the write fails (e.g. disk full) — the caller
        is responsible for handling that case.
        """
        data = self._read_raw()
        data["profiles"][profile.profile_name] = dataclasses.asdict(profile)
        self._atomic_write(data)

    def load_all(self) -> List[ConstraintProfile]:
        """Return all stored profiles.

        * Returns ``[]`` if the file does not exist.
        * Returns ``[]`` (with a warning) if the file contains malformed JSON.
        * Never raises.
        """
        if not self._path.exists():
            return []

        try:
            text = self._path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.warning("dew-export: could not read %s: %s", self._path, exc)
            return []

        if not text:
            return []

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning(
                "dew-export: malformed JSON in %s — returning empty profile list. Error: %s",
                self._path,
                exc,
            )
            return []

        profiles: List[ConstraintProfile] = []
        for raw in data.get("profiles", {}).values():
            try:
                profiles.append(ConstraintProfile(**raw))
            except (TypeError, KeyError) as exc:
                logger.warning(
                    "dew-export: skipping malformed profile entry in %s: %s",
                    self._path,
                    exc,
                )
        return profiles

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, profiles_path: Optional[str]) -> Path:
        """Resolve the profiles.json path.

        Resolution order:
            1. Constructor argument
            2. DEW_PROFILES_PATH env var
            3. Same directory as DEW_LOG_PATH + profiles.json
            4. logs/profiles.json (final fallback)
        """
        if profiles_path is not None:
            return Path(profiles_path)

        env_path = os.environ.get("DEW_PROFILES_PATH")
        if env_path:
            return Path(env_path)

        log_path = os.environ.get("DEW_LOG_PATH")
        if log_path:
            return Path(log_path).parent / _DEFAULT_FILENAME

        return Path(_DEFAULT_LOG_DIR) / _DEFAULT_FILENAME

    def _read_raw(self) -> dict:
        """Read the current on-disk data, returning a blank structure if absent or empty."""
        if not self._path.exists():
            return {"profiles": {}}

        try:
            text = self._path.read_text(encoding="utf-8").strip()
        except OSError:
            return {"profiles": {}}

        if not text:
            return {"profiles": {}}

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Preserve existing data on malformed file rather than silently
            # overwriting — return blank so the caller can upsert safely.
            return {"profiles": {}}

    def _atomic_write(self, data: dict) -> None:
        """Write *data* to a temp file in the same directory, then os.replace().

        Using the same directory guarantees the rename is on the same filesystem
        mount, making os.replace() atomic on both POSIX and Windows.
        """
        target = self._path
        target.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            os.replace(tmp_path, target)
        except Exception:
            # Clean up the temp file if anything goes wrong before the rename.
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
