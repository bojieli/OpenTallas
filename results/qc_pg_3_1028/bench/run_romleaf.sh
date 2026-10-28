#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/wt/qc-pg-3
cd /srv/opentallas-scratch2/claude/qc-pg-3/sim/romleaf
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --trace --trace-depth 5 -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_romleaf_prod --Mdir obj tb_romleaf_prod.sv $R/rtl/physical/ot_qwen_tile_romleaf.sv $R/rtl/hdc/ot_qwen_rom_tile_w12.sv $R/rtl/hdc/ot_hdc_delay.sv $R/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v >build.log 2>&1
for m in 1 2; do ./obj/Vtb_romleaf_prod +MODE=$m >sim_m$m.log 2>&1; python3 ../vcd_activity.py romleaf_m$m.vcd act_m$m --clk tb_romleaf_prod.clk --root romleaf=tb_romleaf_prod.a >act_m$m.log 2>&1; rm -f romleaf_m$m.vcd; done
