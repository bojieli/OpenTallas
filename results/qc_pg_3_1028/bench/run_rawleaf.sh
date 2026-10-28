#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/qc-pg-3/sim/rawleaf
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --trace --trace-underscore --trace-depth 3 -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_rawleaf_prod --Mdir obj tb_rawleaf_prod.sv rawleaf_keep.v models/dff.v dff_async.v models/asap7sc7p5t_AO_RVT_TT_201020.v models/asap7sc7p5t_INVBUF_RVT_TT_201020.v models/asap7sc7p5t_OA_RVT_TT_201020.v models/asap7sc7p5t_SIMPLE_RVT_TT_201020.v >build.log 2>&1
./obj/Vtb_rawleaf_prod >sim.log 2>&1
python3 ../vcd_activity.py rawleaf_prod.vcd activity --clk tb_rawleaf_prod.clk --root rawleaf=tb_rawleaf_prod.dut >activity.log 2>&1
rm -f rawleaf_prod.vcd
