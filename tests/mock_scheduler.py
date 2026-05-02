"""
mock_scheduler.py
=================
Simulates a pre-sanitization hospital scheduling layer for testing.
Generates anonymized graph topology and fires synthetic events.

Zero PHI. Zero patient data. Zero real identifiers.
Node IDs are role + number only. This is what the real sanitizer
would produce before posting to Dew.

Use in tests to simulate:
  - chart-save events (new patient needs routing)
  - constraint-change events (bed/doctor availability updates)
  - batch routing runs
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from tree_topology_heuristics import TreeNode


# ---------------------------------------------------------------------------
# Hospital topology builder
# ---------------------------------------------------------------------------

@dataclass
class HospitalConfig:
    """Configuration for generated hospital topology."""
    n_standard_beds: int = 6
    n_icu_beds: int = 2
    n_maintenance_rooms: int = 2
    n_radiology_units: int = 1
    seed: Optional[int] = None


def build_hospital_graph(config: HospitalConfig = None) -> Dict[str, TreeNode]:
    """
    Build an anonymized hospital graph.
    Triage connects to all standard beds and radiology.
    Standard beds connect to ICU.
    Maintenance rooms are isolated dead-ends (no path to triage).
    Returns a dict of node_id → TreeNode. No PHI anywhere.
    """
    if config is None:
        config = HospitalConfig()

    if config.seed is not None:
        random.seed(config.seed)

    graph: Dict[str, TreeNode] = {}

    bed_ids = [f"bed_{i:02d}" for i in range(1, config.n_standard_beds + 1)]
    icu_ids = [f"icu_{i:02d}" for i in range(1, config.n_icu_beds + 1)]
    maint_ids = [f"maintenance_{i:02d}" for i in range(1, config.n_maintenance_rooms + 1)]
    rad_ids = [f"radiology_{i:02d}" for i in range(1, config.n_radiology_units + 1)]

    # Triage → standard beds + radiology
    graph["triage"] = TreeNode(
        id="triage",
        connections=bed_ids + rad_ids
    )

    # Standard beds ↔ triage, connect to ICU
    for bed_id in bed_ids:
        graph[bed_id] = TreeNode(
            id=bed_id,
            connections=["triage"] + icu_ids
        )

    # ICU ↔ standard beds only
    for icu_id in icu_ids:
        graph[icu_id] = TreeNode(
            id=icu_id,
            connections=bed_ids
        )

    # Radiology ↔ triage only
    for rad_id in rad_ids:
        graph[rad_id] = TreeNode(
            id=rad_id,
            connections=["triage"]
        )

    # Maintenance: isolated — reachable only from each other, never from triage
    for maint_id in maint_ids:
        others = [m for m in maint_ids if m != maint_id]
        graph[maint_id] = TreeNode(
            id=maint_id,
            connections=others
        )

    return graph


def get_available_beds(
    graph: Dict[str, TreeNode],
    occupied: Optional[List[str]] = None
) -> List[str]:
    """Return all bed_* and icu_* node IDs not in the occupied list."""
    occupied_set = set(occupied or [])
    return [
        node_id for node_id in graph
        if (node_id.startswith("bed_") or node_id.startswith("icu_"))
        and node_id not in occupied_set
    ]


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

@dataclass
class ChartSaveEvent:
    """
    Simulates a nurse hitting save on a patient chart.
    Sanitizer has already stripped PHI. Dew receives only:
    - a start node (triage)
    - a set of candidate target nodes (available beds)
    No patient name, no DOB, no MRN — none of those fields exist here.
    """
    event_id: str
    start: str
    candidates: List[str]
    acuity: str  # "standard" | "icu" | "radiology" — routing hint only


@dataclass
class ConstraintChangeEvent:
    """
    Simulates a resource availability update.
    Doctor marks themselves unavailable. Bed goes offline for cleaning.
    Graph node is removed or added from the routing surface.
    """
    event_id: str
    event_type: str     # "bed_offline" | "bed_online" | "icu_offline" | "icu_online"
    node_id: str
    reason: str         # human note for audit log — no PHI


@dataclass
class SchedulerState:
    """Mutable state for the mock scheduler — tracks what's occupied."""
    graph: Dict[str, TreeNode]
    occupied: List[str] = field(default_factory=list)
    offline: List[str] = field(default_factory=list)
    event_counter: int = 0

    def _next_event_id(self) -> str:
        self.event_counter += 1
        return f"EVT_{self.event_counter:04d}"

    def available_beds(self) -> List[str]:
        unavailable = set(self.occupied + self.offline)
        return [
            node_id for node_id in self.graph
            if (node_id.startswith("bed_") or node_id.startswith("icu_"))
            and node_id not in unavailable
        ]

    def fire_chart_save(self, acuity: str = "standard") -> ChartSaveEvent:
        """Generate a chart-save event for a new patient needing routing."""
        candidates = self.available_beds()
        if acuity == "icu":
            candidates = [c for c in candidates if c.startswith("icu_")] or candidates
        elif acuity == "standard":
            candidates = [c for c in candidates if c.startswith("bed_")] or candidates

        return ChartSaveEvent(
            event_id=self._next_event_id(),
            start="triage",
            candidates=candidates,
            acuity=acuity,
        )

    def fire_bed_offline(self, node_id: Optional[str] = None) -> ConstraintChangeEvent:
        """Take a bed offline (cleaning, maintenance, etc)."""
        available = self.available_beds()
        if not available:
            raise RuntimeError("No available beds to take offline.")
        target = node_id or random.choice(available)
        self.offline.append(target)
        return ConstraintChangeEvent(
            event_id=self._next_event_id(),
            event_type="bed_offline",
            node_id=target,
            reason="bed taken offline for scheduled cleaning"
        )

    def fire_bed_online(self, node_id: Optional[str] = None) -> ConstraintChangeEvent:
        """Bring a bed back online."""
        if not self.offline:
            raise RuntimeError("No offline beds to bring back online.")
        target = node_id or self.offline[0]
        if target in self.offline:
            self.offline.remove(target)
        return ConstraintChangeEvent(
            event_id=self._next_event_id(),
            event_type="bed_online",
            node_id=target,
            reason="bed returned to service"
        )

    def admit(self, node_id: str) -> None:
        """Mark a bed as occupied after routing assigns a patient."""
        if node_id not in self.occupied:
            self.occupied.append(node_id)

    def discharge(self, node_id: str) -> None:
        """Free a bed after discharge."""
        if node_id in self.occupied:
            self.occupied.remove(node_id)


# ---------------------------------------------------------------------------
# Convenience builder
# ---------------------------------------------------------------------------

def make_scheduler(config: HospitalConfig = None) -> SchedulerState:
    """Build a SchedulerState with a fresh hospital graph."""
    graph = build_hospital_graph(config or HospitalConfig(seed=42))
    return SchedulerState(graph=graph)
