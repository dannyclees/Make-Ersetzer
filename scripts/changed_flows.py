"""Gibt die Ablauf-Ordner aus, die zwischen zwei Commits geändert wurden (als JSON-Liste).

Ändert sich etwas in shared/, gelten alle Abläufe als geändert.
  python scripts/changed_flows.py <base-sha> <head-sha>
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def all_flows() -> list[str]:
    return sorted(str(p.parent.relative_to(ROOT)) for p in ROOT.glob("*/*/flow.yaml"))


def main(base: str, head: str) -> None:
    flows = all_flows()
    if not base or set(base) == {"0"}:
        print(json.dumps(flows))
        return
    changed = subprocess.run(["git", "diff", "--name-only", base, head], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout.split()
    if any(f.startswith("shared/") for f in changed):
        print(json.dumps(flows))
        return
    print(json.dumps([fl for fl in flows if any(f.startswith(fl + "/") for f in changed)]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2] if len(sys.argv) > 2 else "HEAD")
