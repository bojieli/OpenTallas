#!/bin/bash
set -euo pipefail
cd /
K=$1
MODE=$2
if [[ "$MODE" == synth ]]; then
  exec > "$K/synth.log" 2>&1
  sudo docker run --rm --name codex-svc-sml-native-synth-1209 --memory 16g --memory-swap 16g --cpus 8 -v "$K:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'make DESIGN_CONFIG=/work/config.mk NUM_CORES=8 synth'
elif [[ "$MODE" == bench ]]; then
  exec > "$K/bench.driver.log" 2>&1
  exec python3 -I "$(dirname "$0")/svc_hardening_bench.py" "$K"
else
  echo "unsupported mode: $MODE" >&2
  exit 2
fi
