#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
pids=()
for kind in btab prog vmr; do python3 run_one.py "$kind" > "$kind/model.log" 2>&1 & pids+=("$!"); done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"
