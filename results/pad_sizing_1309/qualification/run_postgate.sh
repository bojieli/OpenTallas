#!/bin/bash
set -e
R=$(cd "$(dirname "$0")" && pwd)
HEAD=/srv/opentallas-scratch2/claude/flow-canary/ab/runs/s81_head_1ae8ebeb0_1025_114536_038973/gen/hd_turn_a
for C in TT FF; do
 docker run --rm --cpus=1 --memory=4g --memory-swap=4g -v "$HEAD":/head:ro -v "$R/postgate_kit":/work -e OT_CORNER=$C -e OT_POSTCTS_GRT=1 -e OT_POSTCTS_TAG=qualification_gate -e ODB=/head/run/results/asap7/dp_hd_turn_a/base/5_1_grt.odb openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/postcts_gate.tcl" > "$R/postgate_$C.log" 2>&1
done
python3 "$R/validate_postgate.py" "$R/postgate_kit"
