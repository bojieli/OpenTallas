#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-qc-a0-activity-0359/rawleaf
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --trace --trace-depth 3 -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_rawleaf_activity --Mdir obj tb_rawleaf_activity.sv rawleaf_keep.v models/dff.v dff_async.v models/asap7sc7p5t_AO_RVT_TT_201020.v models/asap7sc7p5t_INVBUF_RVT_TT_201020.v models/asap7sc7p5t_OA_RVT_TT_201020.v models/asap7sc7p5t_SIMPLE_RVT_TT_201020.v >build.log 2>&1
./obj/Vtb_rawleaf_activity >sim.log 2>&1
