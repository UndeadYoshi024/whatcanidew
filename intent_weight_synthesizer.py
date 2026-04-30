"""
intent_weight_synthesizer
=========================
Converts natural language intent into a structured constraint profile.
The profile is written to the activity log once and never modified.
Dijkstra runs on the weights. The LLM never runs again.

The LLM shapes terrain. The math finds the river.

Requires:
    pip install anthropic

Usage:
    from intent_weight_synthesizer import IntentWeightSynthesizer
    from logger import ActivityLog

    log = ActivityLog("logs/routing_decisions.log")
    synthesizer = IntentWeightSynthesizer(api_key="your-key", log=log)
    profile = synthesizer.synthesize("Get the invoice to the port before the warehouse closes")

    # profile.weights is now ready to apply to your graph edges
    # profile is written to the log — permanent, auditable, never re-run unless intent changes
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional

import anthropic

from logger import ActivityLog


SYSTEM_PROMPT = """You are a constraint synthesizer. Your only job is to convert a user's natural language description of their routing problem into a structured constraint profile. You do not route anything. You do not make decisions. You shape terrain.

INPUT: A natural language statement of intent from a user.

OUTPUT: A JSON object only. No preamble. No explanation. No markdown. Raw JSON.

Schema:
{
  "profile_name": "short_snake_case_identifier",
  "intent_summary": "one sentence, plain english, what the user is trying to do",
  "weights": {
    "time":        0.0,
    "cost":        0.0,
    "risk":        0.0,
    "reliability": 0.0,
    "distance":    0.0
  },
  "constraints": {
    "avoid":      ["list of node or edge types to penalize heavily"],
    "prefer":     ["list of node or edge types to reward with lower weight"],
    "hard_block": ["list of node or edge types that are unreachable, distance -1"]
  },
  "notes": "anything the routing system should know that does not fit above"
}

Rules:
- Weights must sum to 1.0 exactly
- hard_block overrides everything. Those edges do not exist.
- If the user expresses urgency, time weight dominates
- If the user expresses budget concerns, cost weight dominates
- If the user expresses uncertainty or unfamiliarity, reliability weight dominates
- When intent is ambiguous, distribute evenly across time, cost, reliability
- profile_name must be unique, lowercase, underscores only

The profile will be written to an append-only audit log immediately after you return it.
It is permanent. Shape it carefully."""


@dataclass
class ConstraintProfile:
    profile_name: str
    intent_summary: str
    weights: Dict[str, float]
    constraints: Dict[str, List[str]]
    notes: str
    raw_intent: str


class IntentWeightSynthesizer:

    def __init__(self, api_key: str, log: ActivityLog, model: str = "claude-haiku-4-5-20251001") -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.log = log
        self.model = model

    def synthesize(self, user_intent: str, caller: str = "intent_synthesizer") -> ConstraintProfile:
        """
        Convert natural language intent into a constraint profile.
        Writes the profile to the activity log once. Returns the profile.
        The LLM does not run again unless this method is called again.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_intent}]
        )

        raw = response.content[0].text.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"IntentWeightSynthesizer: model returned non-JSON output. Raw: {raw}") from e

        profile = ConstraintProfile(
            profile_name=data["profile_name"],
            intent_summary=data["intent_summary"],
            weights=data["weights"],
            constraints=data.get("constraints", {"avoid": [], "prefer": [], "hard_block": []}),
            notes=data.get("notes", ""),
            raw_intent=user_intent
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
