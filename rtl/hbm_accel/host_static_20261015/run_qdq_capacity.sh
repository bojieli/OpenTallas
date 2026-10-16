#!/usr/bin/env bash
set -euo pipefail
out=${1:?out};mut=${2:-0};mkdir -p "$out"
src=rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_record_calendar.sv
if [[ "$mut" == 1 ]]; then
 python3 - "$src" "$out/mutant.sv" <<'PYM'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text();old='reg [10:0] next_pc;';assert s.count(old)==1
pathlib.Path(sys.argv[2]).write_text(s.replace(old,'reg [9:0] next_pc;'))
PYM
 src="$out/mutant.sv"
fi
iverilog -g2012 -s tb_qdq_compact_capacity -o "$out/sim" "$src" rtl/hbm_accel/host_static_20261015/tb_qdq_compact_capacity.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$out/build.log" 2>&1
vvp "$out/sim" > "$out/run.log" 2>&1
cat "$out/run.log"
grep -q '^QDQ_COMPACT_CAPACITY_PASS' "$out/run.log"
