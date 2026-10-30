#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
R=/srv/opentallas-scratch2/claude/codex-head-start-2249
W=/srv/opentallas-scratch2/claude/wt/codex-head-start-2249
cd "$R"
verilator --cc --exe --build -j 4 --top-module tb_ring_local_start -Wno-fatal --Mdir obj_ring3 tb_ring_local_start.sv "$W/rtl/common/ot_dp_clk_landing_ca.sv" "$W/rtl/common/ot_dp_clk_landing.sv" "$W/rtl/common/ot_meso_fifo.sv" ring_local_start3.cpp > ring3_build.log 2>&1
./obj_ring3/Vtb_ring_local_start > ring3_run.log 2>&1
