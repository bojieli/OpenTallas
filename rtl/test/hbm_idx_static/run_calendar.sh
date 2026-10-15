#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-static-calendar-proof}")
mkdir -p "$out"
python3 tools/hbm_idx_static_calendar.py "$out"
n=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["length"])' "$out/calendar.json")
for m in 0 1;do
 iverilog -g2012 -s tb_calendar_static -Ptb_calendar_static.MUT="$m" -o "$out/p$m.vvp" rtl/hbm_accel/index/ot_hbm_idx_calendar_static.sv rtl/test/hbm_idx_static/tb_calendar_static.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v > "$out/pbuild$m.log" 2>&1
 set +e
 (cd "$out"&&vvp "p$m.vvp" +N="$n") > "$out/prun$m.log" 2>&1
 rc=$?
 set -e
 cat "$out/prun$m.log"
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;fi
done
