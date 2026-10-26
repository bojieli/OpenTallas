#!/bin/bash
set -eu
cd /srv/opentallas-scratch/claude/codex-gl24-1020
mkdir -p out
pids=()
for layer in L24 L28 L32 L36; do
  for view in 01 02 03 10 11 12 13 20 21 22 23 30 31 32 33; do
    VIEWS=$view bash run_layer.sh "$layer" > "out/owner_${layer}_${view}.log" 2>&1 &
    pids+=("$!")
  done
done
rc=0
for pid in "${pids[@]}"; do
  wait "$pid" || rc=1
done
echo "GL24_REMAINING_DONE rc=$rc"
exit "$rc"
