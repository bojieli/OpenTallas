#!/bin/bash
set -euo pipefail
cd /
R=/srv/opentallas-scratch2/claude/codex-hbm-types-1551/q2r_memory
M=$1
D=$R/run/m$M
mkdir -p "$D"
/usr/bin/iverilog -g2012 -DOT_Q2NF_TGTQ1 -o "$D/sim.vvp" "$R/gen/tb.sv" "$R/gen/old_w.sv" "$R/gen/n$M.sv" "$R"/mac/*.v > "$D/build.log" 2>&1
/usr/bin/vvp -n "$D/sim.vvp" +SEED=1 +NPROG=1 +MUT=$M > "$D/run.log" 2>&1
