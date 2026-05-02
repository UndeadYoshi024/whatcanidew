import sys
import json
import copy
import os
import tempfile
from dataclasses import asdict

sys.path.insert(0, "C:/Dev/dew/pypi")

import entry_point
from intent_weight_synthesizer import ConstraintProfile
from obscura import (
    export_profiles,
    import_profiles,
    snapshot,
    rollback,
    export_migration,
    import_migration,
    edit_profile,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_profile(
    profile_name: str = "fast_route",
    raw_intent: str = "Get there as fast as possible",
) -> ConstraintProfile:
    return ConstraintProfile(
        profile_name=profile_name,
        intent_summary="Prioritize speed above all other factors",
        weights={"time": 0.5, "cost": 0.1, "risk": 0.1, "reliability": 0.2, "distance": 0.1},
        constraints={
            "avoid": ["construction_zone"],
            "prefer": ["highway"],
            "hard_block": ["flood_road"],
        },
        notes="Rush delivery",
        raw_intent=raw_intent,
    )


def _make_cache() -> dict:
    return {
        "Get there as fast as possible": _make_profile(
            "fast_route", "Get there as fast as possible"
        ),
        "Cheapest path regardless of time": _make_profile(
            "cheapest_route", "Cheapest path regardless of time"
        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_profile_dicts(obj):
    """Walk a decoded JSON structure and yield every dict that has all six ConstraintProfile fields."""
    _FIELDS = {"profile_name", "intent_summary", "weights", "constraints", "notes", "raw_intent"}
    if isinstance(obj, dict):
        if _FIELDS.issubset(obj.keys()):
            yield obj
        for v in obj.values():
            yield from _find_profile_dicts(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _find_profile_dicts(item)


# ---------------------------------------------------------------------------
# export_profiles / import_profiles — roundtrip
# ---------------------------------------------------------------------------

def test_roundtrip_preserves_all_fields():
    cache = _make_cache()
    restored = import_profiles(export_profiles(cache))

    assert set(restored.keys()) == set(cache.keys())
    for key in cache:
        orig = cache[key]
        rest = restored[key]
        assert isinstance(rest, ConstraintProfile)
        assert rest.profile_name == orig.profile_name
        assert rest.intent_summary == orig.intent_summary
        assert rest.weights == orig.weights
        assert rest.constraints == orig.constraints
        assert rest.notes == orig.notes
        assert rest.raw_intent == orig.raw_intent


def test_roundtrip_weights_sum_to_one():
    cache = _make_cache()
    for profile in import_profiles(export_profiles(cache)).values():
        assert abs(sum(profile.weights.values()) - 1.0) < 0.01


def test_roundtrip_weight_keys():
    cache = _make_cache()
    expected = {"time", "cost", "risk", "reliability", "distance"}
    for profile in import_profiles(export_profiles(cache)).values():
        assert set(profile.weights.keys()) == expected


def test_roundtrip_constraint_keys():
    cache = _make_cache()
    expected = {"avoid", "prefer", "hard_block"}
    for profile in import_profiles(export_profiles(cache)).values():
        assert set(profile.constraints.keys()) == expected


def test_export_profiles_does_not_mutate_cache():
    cache = _make_cache()
    original_keys = set(cache.keys())
    original_profiles = {k: asdict(v) for k, v in cache.items()}
    export_profiles(cache)
    assert set(cache.keys()) == original_keys
    for k, v in cache.items():
        assert asdict(v) == original_profiles[k]


def test_import_profiles_does_not_mutate_input():
    cache = _make_cache()
    serialized = export_profiles(cache)
    serialized_copy = copy.deepcopy(serialized)
    import_profiles(serialized)
    assert serialized == serialized_copy


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------

def test_snapshot_writes_dew_extension():
    cache = _make_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "out.dew")
        snapshot(cache, path)
        assert os.path.exists(path)
        assert path.endswith(".dew")


def test_snapshot_output_is_valid_json():
    cache = _make_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "out.dew")
        snapshot(cache, path)
        with open(path, "r", encoding="utf-8") as f:
            json.loads(f.read())


def test_snapshot_has_top_level_schema_version():
    cache = _make_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "out.dew")
        snapshot(cache, path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
        assert "schema_version" in data


def test_snapshot_encodes_all_constraint_profile_fields():
    cache = _make_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "out.dew")
        snapshot(cache, path)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.loads(f.read())

        found = list(_find_profile_dicts(raw))
        assert len(found) == len(cache), (
            f"Expected {len(cache)} profile records in snapshot, found {len(found)}"
        )
        for pd in found:
            assert "profile_name" in pd
            assert "intent_summary" in pd
            assert "weights" in pd
            assert "constraints" in pd
            assert "notes" in pd
            assert "raw_intent" in pd


def test_snapshot_does_not_mutate_cache():
    cache = _make_cache()
    original_profiles = {k: asdict(v) for k, v in cache.items()}
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot(cache, os.path.join(tmpdir, "out.dew"))
    for k, v in cache.items():
        assert asdict(v) == original_profiles[k]


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------

def test_rollback_returns_equal_cache():
    cache = _make_cache()
    result = rollback(cache)
    assert set(result.keys()) == set(cache.keys())
    for key in cache:
        assert isinstance(result[key], ConstraintProfile)
        assert asdict(result[key]) == asdict(cache[key])


def test_rollback_returns_independent_copy():
    cache = _make_cache()
    result = rollback(cache)
    assert result is not cache
    for key in cache:
        assert result[key] is not cache[key]


def test_rollback_does_not_mutate_input():
    cache = _make_cache()
    original_profiles = {k: asdict(v) for k, v in cache.items()}
    rollback(cache)
    for k, v in cache.items():
        assert asdict(v) == original_profiles[k]


# ---------------------------------------------------------------------------
# export_migration
# ---------------------------------------------------------------------------

def test_export_migration_contains_graph_meta_block():
    cache = _make_cache()
    result = export_migration(cache)
    assert isinstance(result, dict)
    assert "graph_meta" in result
    assert isinstance(result["graph_meta"], dict)


def test_export_migration_does_not_mutate_cache():
    cache = _make_cache()
    original_profiles = {k: asdict(v) for k, v in cache.items()}
    export_migration(cache)
    for k, v in cache.items():
        assert asdict(v) == original_profiles[k]


# ---------------------------------------------------------------------------
# import_migration
# ---------------------------------------------------------------------------

def test_import_migration_returns_tuple():
    cache = _make_cache()
    result = import_migration(export_migration(cache))
    assert isinstance(result, tuple)


def test_import_migration_does_not_mutate_input():
    cache = _make_cache()
    migration_data = export_migration(cache)
    migration_copy = copy.deepcopy(migration_data)
    import_migration(migration_data)
    assert migration_data == migration_copy


# ---------------------------------------------------------------------------
# edit_profile
# ---------------------------------------------------------------------------

_EDIT_KEY = "Get there as fast as possible"
_EDIT_REASON = "User revised safety requirements"


def _edited_result():
    cache = _make_cache()
    new_profile = _make_profile("revised_fast", "Get there fast but safely")
    return cache, edit_profile(cache, _EDIT_KEY, new_profile, reason=_EDIT_REASON), new_profile


def test_edit_profile_tombstones_original_key():
    cache, result, _ = _edited_result()
    assert _EDIT_KEY in result, "tombstoned key must still be present"
    tombstone = result[_EDIT_KEY]
    assert not isinstance(tombstone, ConstraintProfile), (
        "tombstoned entry must not remain a live ConstraintProfile"
    )


def test_edit_profile_tombstone_records_reason():
    _, result, _ = _edited_result()
    tombstone = result[_EDIT_KEY]
    tombstone_repr = json.dumps(tombstone) if isinstance(tombstone, dict) else str(tombstone)
    assert _EDIT_REASON in tombstone_repr


def test_edit_profile_tombstone_records_timestamp():
    _, result, _ = _edited_result()
    tombstone = result[_EDIT_KEY]
    tombstone_repr = json.dumps(tombstone) if isinstance(tombstone, dict) else str(tombstone)
    assert any(c.isdigit() for c in tombstone_repr), "tombstone must contain a timestamp"


def test_edit_profile_inserts_new_entry():
    _, result, new_profile = _edited_result()
    live = [v for v in result.values() if isinstance(v, ConstraintProfile)]
    assert any(p.profile_name == new_profile.profile_name for p in live), (
        "new ConstraintProfile must be present in result"
    )


def test_edit_profile_does_not_mutate_input_cache():
    cache = _make_cache()
    original_keys = set(cache.keys())
    original_profiles = {k: asdict(v) for k, v in cache.items()}
    new_profile = _make_profile("revised_fast", "Get there fast but safely")

    edit_profile(cache, _EDIT_KEY, new_profile, reason=_EDIT_REASON)

    assert set(cache.keys()) == original_keys
    for k, v in cache.items():
        assert asdict(v) == original_profiles[k]


# ---------------------------------------------------------------------------
# schema_version present across all .dew outputs
# ---------------------------------------------------------------------------

def test_schema_version_in_every_dew_output():
    cache = _make_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "schema_check.dew")
        snapshot(cache, path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
        assert "schema_version" in data, "schema_version must be at top level of every .dew file"


# ---------------------------------------------------------------------------
# All .dew outputs are valid JSON
# ---------------------------------------------------------------------------

def test_snapshot_dew_is_always_valid_json():
    for i, profile_name in enumerate(["alpha_route", "beta_route", "gamma_route"]):
        cache = {f"intent_{i}": _make_profile(profile_name, f"intent_{i}")}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, f"run_{i}.dew")
            snapshot(cache, path)
            with open(path, "r", encoding="utf-8") as f:
                json.loads(f.read())


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
