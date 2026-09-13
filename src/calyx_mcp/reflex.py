"""
MBON Reflex Decision Engine
Evaluates code patterns against synaptic weights to return instant Avoid / Safe / Neutral reflexes.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import numpy as np

from .hasher import FlyLSHHasher
from .memory import MushroomBodyMemory


@dataclass
class ReflexOutcome:
    """Reflex evaluation result"""
    status: str  # 'avoid', 'safe', 'neutral'
    valence: float  # Mean weight of active synapses
    confidence: float  # Distance from neutral baseline (1.0)
    warning: Optional[str] = None
    recommendation: Optional[str] = None
    similarity_with_past_bugs: float = 0.0


class ReflexDecisionEngine:
    """
    Evaluates proposed code patterns and triggers immediate behavioral reflexes.
    """

    def __init__(self, memory: MushroomBodyMemory):
        self.memory = memory
        self.hasher = memory.hasher

    async def evaluate_reflex(self, code: str, context: Optional[str] = None) -> ReflexOutcome:
        """
        Instant (<1ms) matrix evaluation of proposed code against Mushroom Body synaptic weights.
        """
        rep = self.hasher.hash_code(code)
        active_weights = self.memory.weights[rep.active_indices]
        valence = float(np.mean(active_weights))

        # Baseline is 1.0 (pristine/neutral)
        confidence = float(abs(valence - 1.0) / 1.0)

        # Check nearest previously punished bug records
        matches = await self.memory.query_similarity(code, top_k=3)
        past_bug_match = 0.0
        bug_reason = None
        
        for m in matches:
            if m["outcome"].lower() in ["failure", "failed", "bug", "error"] and m["similarity"] > 0.35:
                if m["similarity"] > past_bug_match:
                    past_bug_match = m["similarity"]
                    bug_reason = m.get("error_message") or "Previously caused a unit test failure or runtime bug."

        # Decision Thresholds
        if valence < 0.85 or past_bug_match >= 0.65:
            warning_msg = (
                f"High resemblance ({int(past_bug_match*100)}%) to a previously punished bug pattern: '{bug_reason}'"
                if bug_reason else
                f"Negative synaptic valence ({valence:.2f} < 0.85). Pattern associated with past failures."
            )
            return ReflexOutcome(
                status="avoid",
                valence=round(valence, 4),
                confidence=round(max(confidence, past_bug_match), 4),
                warning=warning_msg,
                recommendation="Review code logic, check edge cases, or adopt an alternative implementation.",
                similarity_with_past_bugs=round(past_bug_match, 4)
            )
            
        elif valence > 1.15:
            return ReflexOutcome(
                status="safe",
                valence=round(valence, 4),
                confidence=round(confidence, 4),
                warning=None,
                recommendation="Positive synaptic valence. Code pattern matches previously rewarded/verified implementations.",
                similarity_with_past_bugs=round(past_bug_match, 4)
            )
            
        else:
            return ReflexOutcome(
                status="neutral",
                valence=round(valence, 4),
                confidence=round(confidence, 4),
                warning=None,
                recommendation="Novel or unverified code pattern. Proceed normally and record outcome after testing.",
                similarity_with_past_bugs=round(past_bug_match, 4)
            )
