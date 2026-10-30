#!/bin/bash
set -euo pipefail
kit=$1
docker run --rm --memory=12g --cpus=4 -v "$kit":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -exit /work/swap_lvt.tcl > /work/clock_lvt_swap.log 2>&1
for c in TT FF; do
  OT_CORNER=$c ODB=$(find /work/run/results/asap7 -name 4_cts.odb | head -1) openroad -exit /work/postcts_gate.tcl > /work/clock_lvt_${c}.log 2>&1 || true
done
chown -R '"$(id -u):$(id -g)"' /work
'
