#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/wt/codex-qc-a0-activity-0359
out=/srv/opentallas-scratch2/claude/codex-qc-a0-activity-0359/romleaf
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing --trace --trace-depth 5 -j 2 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qwen_romleaf_1552 --Mdir "$out/obj" "$out/tb_qwen_romleaf_1552_trace.sv" rtl/physical/ot_qwen_tile_romleaf.sv rtl/hdc/ot_qwen_rom_tile_w12.sv rtl/hdc/ot_hdc_delay.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v >"$out/build.log" 2>&1
cd "$out"
./obj/Vtb_qwen_romleaf_1552 > sim.log 2>&1
python3 /srv/opentallas-scratch2/claude/wt/codex-qc-a0-activity-0359/tools/pg_activity/vcd_activity.py romleaf.vcd activity --clk tb_qwen_romleaf_1552.clk --root romleaf=tb_qwen_romleaf_1552.a >activity.log 2>&1
