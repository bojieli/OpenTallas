#!/bin/bash
set -euo pipefail
lane=/srv/opentallas-scratch/claude/codex-s81-c199-freeclk-synth
original=/srv/opentallas-scratch/claude/ref_gate/s81sf_bfcol_c199r-20261019-072007
mkdir -p "$lane/work"
cp "$original/routes/gate/work/orfs/config.mk" "$lane/work/config.mk"
printf '\nexport VERILOG_DEFINES += -DOT_BF_TILE_FREECLK\n' >> "$lane/work/config.mk"
docker run --rm -e LEC_CHECK=0 -v "$original/src":/src:ro -v "$lane/ot_v41_tile_clk.sv":/src/rtl/v41rom/ot_v41_tile_clk.sv:ro -v "$lane/work":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > "$lane/synth.log" 2>&1
