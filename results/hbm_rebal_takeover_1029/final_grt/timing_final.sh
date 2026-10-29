#!/bin/bash
set -eu
K=/srv/opentallas-scratch2/claude/codex-hbm-rebal-0310/kit
mkdir -p "$K/final_grt"
# Separate output namespace; preserve all prior gate verdicts.
sed 's@/work/postcts_gate_@/work/final_grt/postcts_gate_@g' "$K/postcts_gate.tcl" > "$K/final_grt/postcts_gate.tcl"
docker run --rm --cpus 4 --memory 16g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
for c in TT FF; do
 OT_POSTCTS_GRT=1 OT_CORNER=$c ODB=/work/run/results/asap7/hbc_hnx_lane_x/base/5_1_grt.odb openroad -no_init -exit /work/final_grt/postcts_gate.tcl > /work/final_grt/gate_$c.log 2>&1 || exit $?
done
'
