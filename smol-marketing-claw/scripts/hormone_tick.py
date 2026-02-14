"""SessionStart hook — apply hormone decay."""

import json
import sys
from pathlib import Path

HORMONES_FILE = Path(__file__).resolve().parent.parent.parent / "memory" / "hormones.json"


def main():
    if not HORMONES_FILE.exists():
        return

    try:
        with open(HORMONES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        cortisol = float(data.get("cortisol", 0.0))
        dopamine = float(data.get("dopamine_snapshot", 0.5))
        tick_count = int(data.get("tick_count", 0))

        # Apply decay
        dopamine += (0.5 - dopamine) * 0.10
        cortisol += (0.0 - cortisol) * 0.02
        tick_count += 1

        # Clamp
        dopamine = max(0.0, min(1.0, dopamine))
        cortisol = max(0.0, min(1.0, cortisol))

        data["cortisol"] = cortisol
        data["dopamine_snapshot"] = dopamine
        data["tick_count"] = tick_count

        with open(HORMONES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"Hormone tick: dopamine={dopamine:.3f}, cortisol={cortisol:.3f}, tick={tick_count}", file=sys.stderr)
    except Exception as e:
        print(f"Hormone tick failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
