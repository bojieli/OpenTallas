#!/bin/bash
set -uo pipefail
r=/srv/opentallas-scratch2/claude/ce9-cfg-probe-1029; k=/srv/opentallas-scratch2/claude/codex-s81-cfg-pin1029/kits/ot_s81_cfg7_seq_bfp_explicitpin1029
for cor in TT FF; do
 docker run --rm --name ce9-cfg-probe-$cor --cpus 2 --memory 8g --memory-swap 8g -v "$r/timing":/work -v "$k":/kit:ro -v "$r/probe.tcl":/probe.tcl:ro -e OT_CORNER="$cor" -e OT_POSTCTS_GRT=1 -e ODB=/kit/run/results/asap7/kl_ot_s81_cfg7_seq_bfp_explicitpin1029/base/5_1_grt.odb -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /probe.tcl" > "$r/timing/probe_$cor.log" 2>&1 &
done; wait
