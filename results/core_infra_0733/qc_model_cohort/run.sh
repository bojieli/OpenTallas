#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for kind in btab prog vmr; do
 PYTHONPATH=$PWD python3 core_infra_search.py "$kind/input.json" --out "$kind/out" > "$kind/model.log" 2>&1 &
done
wait
