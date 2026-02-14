"""Digital hormone system — 3-axis emotional state for AI behavior control."""

import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from src.config import MODEL_ALIASES


@dataclass
class HormoneState:
    """Three-axis hormone state."""

    dopamine: float = 0.5  # Reward signal (volatile, resets on restart)
    cortisol: float = 0.0  # Stress signal (persistent across restarts)
    energy: float = 1.0  # Resource budget (derived from UsageTracker)
    tick_count: int = 0  # Number of think() calls


@dataclass
class HormoneControlParams:
    """Behavioral control parameters derived from hormone state."""

    model: str = "sonnet"
    creativity_instruction: str = ""
    persona_modifier: str = ""
    posting_frequency_multiplier: float = 1.0
    max_response_length: str = "normal"


class DigitalHormones:
    """Manages a 3-axis digital hormone system that controls AI behavior."""

    def __init__(
        self,
        state_file: str = "memory/hormones.json",
        usage_tracker=None,
    ):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(exist_ok=True)
        self.usage_tracker = usage_tracker
        self.state = self._load_state()

    def _load_state(self) -> HormoneState:
        """Load persisted state. Cortisol and tick_count survive restarts; dopamine resets to 0.5."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return HormoneState(
                    dopamine=0.5,  # volatile — always reset
                    cortisol=float(data.get("cortisol", 0.0)),
                    energy=self._calc_energy(),
                    tick_count=int(data.get("tick_count", 0)),
                )
            except Exception:
                pass
        return HormoneState(energy=self._calc_energy())

    def save_state(self):
        """Persist hormone state to disk."""
        data = {
            "cortisol": self.state.cortisol,
            "tick_count": self.state.tick_count,
            "dopamine_snapshot": self.state.dopamine,
            "energy_snapshot": self.state.energy,
        }
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save hormone state: {e}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------
    def decay(self):
        """One tick of hormone decay. Called at start of each think() cycle."""
        self.state.tick_count += 1

        # Dopamine → 0.5 (neutral) at 10% per tick
        self.state.dopamine += (0.5 - self.state.dopamine) * 0.10

        # Cortisol → 0.0 at 2% per tick
        self.state.cortisol += (0.0 - self.state.cortisol) * 0.02

        # Energy from UsageTracker
        self.state.energy = self._calc_energy()

        # Clamp all values
        self._clamp()

    # ------------------------------------------------------------------
    # Triggers
    # ------------------------------------------------------------------
    def trigger_dopamine(self, delta: float):
        """Event-based dopamine change."""
        self.state.dopamine = max(0.0, min(1.0, self.state.dopamine + delta))

    def trigger_cortisol(self, delta: float):
        """Event-based cortisol change."""
        self.state.cortisol = max(0.0, min(1.0, self.state.cortisol + delta))

    # ------------------------------------------------------------------
    # Control parameters
    # ------------------------------------------------------------------
    def get_control_params(self) -> HormoneControlParams:
        """Derive behavioral control parameters from current hormone state."""
        s = self.state
        params = HormoneControlParams()

        # Model selection: low energy → haiku (cheap)
        if s.energy < 0.2:
            params.model = "haiku"
        else:
            params.model = "sonnet"

        # Creativity instruction
        if s.cortisol >= 0.8:
            params.creativity_instruction = (
                "Be extremely cautious and precise. "
                "Avoid risky suggestions. Stick to proven approaches."
            )
        elif s.dopamine > 0.7:
            params.creativity_instruction = (
                "Be creative and experimental. "
                "Try novel approaches and bold suggestions."
            )
        else:
            params.creativity_instruction = (
                "Balance creativity with reliability. "
                "Suggest practical improvements."
            )

        # Persona modifier
        label = self._label_state()
        params.persona_modifier = (
            f"[Current Emotional State: {label}] "
            f"Dopamine={s.dopamine:.2f} Cortisol={s.cortisol:.2f} Energy={s.energy:.2f}. "
            f"{params.creativity_instruction}"
        )

        # Posting frequency
        if s.cortisol >= 0.7:
            params.posting_frequency_multiplier = 0.25
        elif s.dopamine > 0.7:
            params.posting_frequency_multiplier = 1.5
        else:
            params.posting_frequency_multiplier = 1.0

        # Response length
        if s.energy < 0.3:
            params.max_response_length = "short"
        elif s.dopamine > 0.7:
            params.max_response_length = "verbose"
        else:
            params.max_response_length = "normal"

        return params

    # ------------------------------------------------------------------
    # Status / labels
    # ------------------------------------------------------------------
    def get_status_dict(self) -> dict:
        """Return a dictionary for API / dashboard display."""
        params = self.get_control_params()
        return {
            "dopamine": round(self.state.dopamine, 3),
            "cortisol": round(self.state.cortisol, 3),
            "energy": round(self.state.energy, 3),
            "tick_count": self.state.tick_count,
            "label": self._label_state(),
            "effective_model": MODEL_ALIASES.get(params.model, params.model),
            "creativity_mode": params.creativity_instruction[:40],
            "posting_multiplier": params.posting_frequency_multiplier,
            "response_length": params.max_response_length,
        }

    def _label_state(self) -> str:
        """Human-readable emotional label."""
        s = self.state
        if s.cortisol >= 0.8:
            return "defensive"
        if s.cortisol >= 0.5:
            return "anxious"
        if s.dopamine > 0.7:
            return "excited"
        if s.dopamine < 0.3:
            return "lethargic"
        if s.energy < 0.2:
            return "exhausted"
        return "balanced"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _calc_energy(self) -> float:
        """Derive energy from UsageTracker daily usage ratio."""
        if not self.usage_tracker:
            return 1.0
        try:
            status = self.usage_tracker.get_status()
            used = status["calls_today"]
            limit = status["limits"]["per_day"]
            if limit <= 0:
                return 1.0
            return max(0.0, min(1.0, 1.0 - (used / limit)))
        except Exception:
            return 1.0

    def _clamp(self):
        """Clamp all values to [0, 1]."""
        self.state.dopamine = max(0.0, min(1.0, self.state.dopamine))
        self.state.cortisol = max(0.0, min(1.0, self.state.cortisol))
        self.state.energy = max(0.0, min(1.0, self.state.energy))
