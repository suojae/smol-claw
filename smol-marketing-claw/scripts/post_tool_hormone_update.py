"""PostToolUse hook — boost dopamine after successful SNS posting."""

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

        # Boost dopamine for successful posting
        dopamine = float(data.get("dopamine_snapshot", 0.5))
        dopamine = min(1.0, dopamine + 0.1)

        data["dopamine_snapshot"] = dopamine

        with open(HORMONES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"Post hormone update: dopamine={dopamine:.3f}", file=sys.stderr)
    except Exception as e:
        print(f"Post hormone update failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
