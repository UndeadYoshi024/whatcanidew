"""
test_hospital.py
================
End-to-end integration test: mock_scheduler → Dew pipeline.
This is the demo. A full hospital shift runs through the system.
No PHI. No API key. Fully deterministic. Real routing math runs on real graphs.

This is the test that answers: "does it dew what we say it dews?"
"""

import pytest
from pathlib import Path
from unittest.mock import patch

import entry_point as ep
from entry_point import route
from tree_topology_heuristics import TreeTopologyHeuristics
from graph_weight_mapper import apply_weights
from logger import ActivityLog
from intent_weight_synthesizer import ConstraintProfile

from mock_scheduler import (
    build_hospital_graph,
    HospitalConfig,
    make_scheduler,
    SchedulerState,
)

HOSPITAL_PROFILE = ConstraintProfile(
    profile_name="hospital_triage_routing",
    intent_summary="Route patients from triage to nearest available bed, avoid maintenance.",
    weights={"time": 0.4, "cost": 0.1, "risk": 0.2, "reliability": 0.2, "distance": 0.1},
    constraints={
        "avoid": ["radiology_01"],
        "prefer": ["bed_01", "bed_03"],
        "hard_block": ["maintenance_01", "maintenance_02"],
    },
    notes="Never route through maintenance. ICU only if no standard bed available.",
    raw_intent="route patients from triage to nearest available bed, avoid maintenance rooms"
)


@pytest.fixture(autouse=True)
def clear_cache():
    ep._profile_cache.clear()
    yield
    ep._profile_cache.clear()


@pytest.fixture
def scheduler():
    return make_scheduler(HospitalConfig(
        n_standard_beds=6,
        n_icu_beds=2,
        n_maintenance_rooms=2,
        n_radiology_units=1,
        seed=42
    ))


class TestHospitalGraphStructure:

    def test_triage_node_exists(self, scheduler):
        assert "triage" in scheduler.graph

    def test_standard_beds_exist(self, scheduler):
        beds = [n for n in scheduler.graph if n.startswith("bed_")]
        assert len(beds) == 6

    def test_icu_beds_exist(self, scheduler):
        icus = [n for n in scheduler.graph if n.startswith("icu_")]
        assert len(icus) == 2

    def test_maintenance_rooms_exist(self, scheduler):
        maints = [n for n in scheduler.graph if n.startswith("maintenance_")]
        assert len(maints) == 2

    def test_triage_connects_to_all_beds(self, scheduler):
        triage_conns = scheduler.graph["triage"].connections
        beds = [n for n in scheduler.graph if n.startswith("bed_")]
        for bed in beds:
            assert bed in triage_conns

    def test_maintenance_not_reachable_from_triage(self, scheduler):
        """Maintenance rooms must be structurally isolated — not just profiled away."""
        for maint_id in [n for n in scheduler.graph if n.startswith("maintenance_")]:
            result = TreeTopologyHeuristics.find_path(scheduler.graph, "triage", maint_id)
            assert result.distance == -1, \
                f"Maintenance room {maint_id} should be unreachable from triage"


class TestMockSchedulerEvents:

    def test_chart_save_returns_candidates(self, scheduler):
        event = scheduler.fire_chart_save()
        assert len(event.candidates) > 0

    def test_chart_save_start_is_triage(self, scheduler):
        event = scheduler.fire_chart_save()
        assert event.start == "triage"

    def test_chart_save_candidates_are_beds(self, scheduler):
        event = scheduler.fire_chart_save()
        for c in event.candidates:
            assert c.startswith("bed_") or c.startswith("icu_")

    def test_chart_save_no_phi_in_candidates(self, scheduler):
        """Candidates must never contain patient-identifiable strings."""
        event = scheduler.fire_chart_save()
        phi_markers = ["patient", "mrn", "dob", "ssn", "name", "id_"]
        for c in event.candidates:
            for marker in phi_markers:
                assert marker not in c.lower()

    def test_bed_offline_removes_from_available(self, scheduler):
        before = len(scheduler.available_beds())
        scheduler.fire_bed_offline()
        after = len(scheduler.available_beds())
        assert after == before - 1

    def test_bed_online_restores_availability(self, scheduler):
        scheduler.fire_bed_offline()
        before = len(scheduler.available_beds())
        scheduler.fire_bed_online()
        after = len(scheduler.available_beds())
        assert after == before + 1

    def test_admit_reduces_available_beds(self, scheduler):
        beds = scheduler.available_beds()
        before = len(beds)
        scheduler.admit(beds[0])
        assert len(scheduler.available_beds()) == before - 1

    def test_discharge_restores_available_beds(self, scheduler):
        beds = scheduler.available_beds()
        scheduler.admit(beds[0])
        before = len(scheduler.available_beds())
        scheduler.discharge(beds[0])
        assert len(scheduler.available_beds()) == before + 1

    def test_event_ids_are_sequential(self, scheduler):
        e1 = scheduler.fire_chart_save()
        e2 = scheduler.fire_chart_save()
        e3 = scheduler.fire_bed_offline()
        assert e1.event_id == "EVT_0001"
        assert e2.event_id == "EVT_0002"
        assert e3.event_id == "EVT_0003"

    def test_icu_acuity_prefers_icu_beds(self, scheduler):
        event = scheduler.fire_chart_save(acuity="icu")
        icu_candidates = [c for c in event.candidates if c.startswith("icu_")]
        assert len(icu_candidates) > 0


class TestFullRoutingPipeline:

    def test_route_patient_to_nearest_bed(self, scheduler, tmp_path):
        """Core scenario: chart save → Dew routes patient to nearest available bed."""
        event = scheduler.fire_chart_save(acuity="standard")
        weighted_graph = apply_weights(scheduler.graph, HOSPITAL_PROFILE)
        result = TreeTopologyHeuristics.find_nearest(
            weighted_graph, event.start, event.candidates
        )
        assert result.target_id is not None
        assert result.distance > 0
        assert result.path[0] == "triage"
        assert result.path[-1] == result.target_id

    def test_preferred_beds_routed_first(self, scheduler):
        """With fresh hospital, preferred beds (bed_01, bed_03) should win."""
        event = scheduler.fire_chart_save(acuity="standard")
        weighted_graph = apply_weights(scheduler.graph, HOSPITAL_PROFILE)
        result = TreeTopologyHeuristics.find_nearest(
            weighted_graph, event.start, event.candidates
        )
        assert result.target_id in ("bed_01", "bed_03")

    def test_admit_then_reroute_skips_occupied(self, scheduler):
        """After admitting bed_01 and bed_03, routing should land elsewhere."""
        event = scheduler.fire_chart_save(acuity="standard")
        weighted_graph = apply_weights(scheduler.graph, HOSPITAL_PROFILE)
        result1 = TreeTopologyHeuristics.find_nearest(
            weighted_graph, event.start, event.candidates
        )
        scheduler.admit(result1.target_id)

        event2 = scheduler.fire_chart_save(acuity="standard")
        result2 = TreeTopologyHeuristics.find_nearest(
            weighted_graph, event2.start, event2.candidates
        )
        assert result2.target_id != result1.target_id

    def test_full_ward_no_available_beds(self, scheduler):
        """Admit all beds — routing should return no reachable target."""
        all_beds = scheduler.available_beds()
        for bed in all_beds:
            scheduler.admit(bed)
        event = scheduler.fire_chart_save()
        assert len(event.candidates) == 0

    def test_constraint_change_updates_routing(self, scheduler):
        """After a bed goes offline, routing should avoid it."""
        event1 = scheduler.fire_chart_save(acuity="standard")
        weighted_graph = apply_weights(scheduler.graph, HOSPITAL_PROFILE)
        result1 = TreeTopologyHeuristics.find_nearest(
            weighted_graph, event1.start, event1.candidates
        )
        # Take that bed offline
        scheduler.fire_bed_offline(result1.target_id)
        event2 = scheduler.fire_chart_save(acuity="standard")
        result2 = TreeTopologyHeuristics.find_nearest(
            weighted_graph, event2.start, event2.candidates
        )
        assert result2.target_id != result1.target_id

    def test_entry_point_route_writes_audit_log(self, scheduler, tmp_path):
        """Full entry_point pipeline writes a readable audit log entry."""
        log_path = str(tmp_path / "hospital_audit.log")
        event = scheduler.fire_chart_save(acuity="standard")

        with patch("entry_point.IntentWeightSynthesizer") as MockSynth:
            MockSynth.return_value.synthesize.return_value = HOSPITAL_PROFILE
            result = route(
                user_intent="route patient to nearest available bed, avoid maintenance",
                graph=scheduler.graph,
                start=event.start,
                target=event.candidates[0],
                log_path=log_path,
            )

        content = Path(log_path).read_text()
        assert "FROM: triage" in content
        assert "CALLER: entry_point" in content
        assert result.distance > 0

    def test_synthesizer_runs_once_across_full_shift(self, scheduler, tmp_path):
        """Simulate a full shift — synthesize called exactly once, cache holds."""
        log_path = str(tmp_path / "shift.log")
        intent = "route patient to nearest available bed, avoid maintenance"

        with patch("entry_point.IntentWeightSynthesizer") as MockSynth:
            instance = MockSynth.return_value
            instance.synthesize.return_value = HOSPITAL_PROFILE

            for _ in range(10):
                event = scheduler.fire_chart_save()
                if not event.candidates:
                    break
                result = route(
                    user_intent=intent,
                    graph=scheduler.graph,
                    start=event.start,
                    target=event.candidates[0],
                    log_path=log_path,
                )
                if result.target_id if hasattr(result, "target_id") else result.path:
                    scheduler.admit(event.candidates[0])

        assert instance.synthesize.call_count == 1, \
            "Synthesizer should run exactly once — the cache must hold across the full shift"
