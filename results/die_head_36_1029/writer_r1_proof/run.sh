#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd /srv/opentallas-scratch2/claude/codex-head-writer-r1-2249
verilator --cc --exe --build -j 4 --top-module tb_ring_local_start -Wno-fatal --Mdir obj tb_ring_local_start.sv ot_dp_clk_landing_ca.sv ot_dp_clk_landing.sv ot_meso_fifo.sv ring_local_start3.cpp > build.log 2>&1
./obj/Vtb_ring_local_start > run.log 2>&1
cat run.log
