#!/usr/bin/env bash
# Führt die Tests jedes Ablaufs einzeln aus (jeder Ablauf hat eigene Module wie flow.py).
set -euo pipefail
cd "$(dirname "$0")/.."
status=0
for f in */*/flow.yaml; do
  dir="$(dirname "$f")"
  [ -d "$dir/tests" ] || continue
  echo "==> $dir"
  python -m pytest -q "$dir/tests" || status=1
done
exit $status
