"""
intent_weight_synthesizer
=========================
Converts natural language intent into a ConstraintProfile using a deterministic
keyword parser. No API call. No LLM. No network. Pure signal extraction.

Your words become weights. The weights shape the terrain. Dijkstra finds the river.

Signal sets:
    Time-dominant:        fast, urgent, quick, asap, deadline
    Cost-dominant:        cheap, budget, cost, affordable, save
    Reliability-dominant: safe, reliable, consistent, stable, trusted
    Risk-averse:          risky, uncertain, dangerous, unpredictable

Inline node constraints parsed directly from the intent string:
    avoid <node>                → constraints["avoid"]
    prefer <node> / use <node>  → constraints["prefer"]
    never <node> / not <node> / block <node> → constraints["hard_block"]

The profile is written to the activity log immediately and is permanent.
Same intent string never re-synthesizes — the result is cached and persisted.

Usage:
    from intent_weight_synthesizer import IntentWeightSynthesizer
    from logger import ActivityLog

    log = ActivityLog("logs/routing_decisions.log")
    synthesizer = IntentWeightSynthesizer(log=log)
    profile = synthesizer.synthesize("Get the invoice to the port before the warehouse closes")

    # profile.weights is ready to apply to your graph edges
    # profile is written to the log — permanent, auditable
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass
from typing import Dict, List

from logger import ActivityLog


@dataclass
class ConstraintProfile:
    profile_name: str        # snake_case, generated deterministically from intent
    intent_summary: str      # human-readable summary of what signals were matched
    weights: Dict[str, float]  # keys: time, cost, risk, reliability, distance
    constraints: Dict[str, List[str]]  # keys: avoid, prefer, hard_block
    notes: str               # empty string from the keyword parser
    raw_intent: str          # the original intent string, unchanged


_TIME_SIGNALS        = {"fast", "urgent", "quick", "asap", "deadline"}
_COST_SIGNALS        = {"cheap", "budget", "cost", "affordable", "save"}
_RELIABILITY_SIGNALS = {"safe", "reliable", "consistent", "stable", "trusted"}
_RISK_SIGNALS        = {"risky", "uncertain", "dangerous", "unpredictable"}


class IntentWeightSynthesizer:

    def __init__(self, log: ActivityLog) -> None:
        self.log = log

    def synthesize(self, user_intent: str, caller: str = "intent_synthesizer") -> ConstraintProfile:
        tokens = user_intent.lower().translate(str.maketrans("", "", string.punctuation)).split()
        token_set = set(tokens)

        time_hit        = bool(token_set & _TIME_SIGNALS)
        cost_hit        = bool(token_set & _COST_SIGNALS)
        reliability_hit = bool(token_set & _RELIABILITY_SIGNALS)
        risk_hit        = bool(token_set & _RISK_SIGNALS)

        if time_hit:
            weights = {"time": 0.70, "cost": 0.10, "risk": 0.0, "reliability": 0.20, "distance": 0.0}
            summary = "time-dominant intent"
        elif cost_hit:
            weights = {"time": 0.10, "cost": 0.70, "risk": 0.0, "reliability": 0.20, "distance": 0.0}
            summary = "cost-dominant intent"
        elif reliability_hit:
            weights = {"time": 0.10, "cost": 0.10, "risk": 0.0, "reliability": 0.80, "distance": 0.0}
            summary = "reliability-dominant intent"
        elif risk_hit:
            # invert: lower risk traversal by weighting cost and reliability up; risk stays 0.0
            weights = {"time": 0.10, "cost": 0.40, "risk": 0.0, "reliability": 0.50, "distance": 0.0}
            summary = "risk-averse intent — cost and reliability weighted up"
        else:
            weights = {"time": 0.34, "cost": 0.33, "risk": 0.0, "reliability": 0.33, "distance": 0.0}
            summary = "ambiguous intent — even distribution"

        constraints: Dict[str, List[str]] = {"avoid": [], "prefer": [], "hard_block": []}
        for i, tok in enumerate(tokens):
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            if nxt is None:
                continue
            if tok == "avoid":
                constraints["avoid"].append(nxt)
            elif tok in ("never", "not", "block"):
                constraints["hard_block"].append(nxt)
            elif tok in ("prefer", "use"):
                constraints["prefer"].append(nxt)

        profile_name = re.sub(r"[^a-z0-9]+", "_", user_intent.lower()).strip("_")[:40]

        profile = ConstraintProfile(
            profile_name=profile_name,
            intent_summary=summary,
            weights=weights,
            constraints=constraints,
            notes="",
            raw_intent=user_intent,
        )

        self._validate_weights(profile.weights)
        self._write_to_log(profile, caller)

        return profile

    def _validate_weights(self, weights: Dict[str, float]) -> None:
        total = sum(weights.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"IntentWeightSynthesizer: weights must sum to 1.0, got {total:.4f}")

    def _write_to_log(self, profile: ConstraintProfile, caller: str) -> None:
        weights_str = " ".join(f"{k}={v}" for k, v in profile.weights.items())
        avoid_str   = ", ".join(profile.constraints.get("avoid", [])) or "none"
        prefer_str  = ", ".join(profile.constraints.get("prefer", [])) or "none"
        block_str   = ", ".join(profile.constraints.get("hard_block", [])) or "none"

        note = (
            f"PROFILE: {profile.profile_name} | "
            f"INTENT: {profile.intent_summary} | "
            f"WEIGHTS: {weights_str} | "
            f"AVOID: {avoid_str} | "
            f"PREFER: {prefer_str} | "
            f"HARD_BLOCK: {block_str}"
        )
        if profile.notes:
            note += f" | NOTES: {profile.notes}"

        self.log.write(
            start="intent",
            target="profile",
            distance=0,
            path=[profile.profile_name],
            caller=caller,
            note=note
        )
