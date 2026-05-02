from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intent_weight_synthesizer import ConstraintProfile

import copy
import dataclasses
import json
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Union


def export_profiles(cache: dict) -> dict:
    return {
        key: dataclasses.asdict(value) if isinstance(value, ConstraintProfile) else value
        for key, value in cache.items()
    }


def import_profiles(data: dict) -> dict[str, ConstraintProfile]:
    return {key: ConstraintProfile(**fields) for key, fields in data.items()}


def snapshot(cache: dict, path: str) -> None:
    payload = {
        "schema_version": "1.0",
        "profiles": export_profiles(cache),
    }
    target = os.path.abspath(path)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def rollback(cache: dict) -> dict[str, ConstraintProfile]:
    return copy.deepcopy(cache)


def export_migration(cache: dict) -> dict:
    return {
        "profiles": export_profiles(cache),
        "graph_meta": {},
    }


def import_migration(data: dict) -> tuple[dict[str, ConstraintProfile], dict]:
    profiles = import_profiles(data["profiles"])
    graph_meta = data.get("graph_meta", {})
    return profiles, graph_meta


def edit_profile(
    cache: dict,
    intent_key: str,
    updated: ConstraintProfile,
    reason: str,
) -> dict[str, Union[ConstraintProfile, dict]]:
    tombstone = dataclasses.asdict(cache[intent_key])
    tombstone["superseded_at"] = datetime.now(timezone.utc).isoformat()
    tombstone["reason"] = reason

    new_cache: dict = {k: v for k, v in cache.items()}
    new_cache[intent_key] = tombstone
    new_cache[updated.raw_intent] = updated
    return new_cache
