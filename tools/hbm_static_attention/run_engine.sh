#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 tools/hbm_static_attention/prepare_engine.py --out "$out/vectors" > "$out/prepare.log" 2>&1
"$vl" --binary --timing --hierarchical -O1 -j ${JOBS:-4} -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
 --unroll-count 128 --unroll-limit 131072 --output-split 20000 --output-split-cfuncs 1000 --top-module tb_hbm_attn_calendar --Mdir "$out/obj" -o sim \
 tools/hbm_static_attention/arithmetic_hierarchy.vlt rtl/hdc/v41x/static/ot_hdc_v41x_attn_calendar.sv rtl/hdc/v41x/static/ot_hbm_attn_event_program.sv \
 rtl/hdc/v41x/ot_hdc_v41x_attn.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv \
 rtl/hdc/ot_hdc_fastfp.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
 rtl/test/hbm_accel/generic/tb_hbm_attn_calendar.sv > "$out/build.log" 2>&1
python3 tools/hbm_static_attention/check_nba_loop_shadow.py "$out/obj" > "$out/nba_shadow.txt"
for m in 0 1 2 3;do
 set +e;"$out/obj/sim" +DIR="$out/vectors" +MUT=$m > "$out/m$m.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/m$m.rc"
 if [ "$m" = 0 ];then grep -q 'PASS ATT_CALENDAR_FULL' "$out/m$m.log";else grep -qE 'ATT_CALENDAR (fault|score mismatch|PV mismatch)' "$out/m$m.log";fi
done
echo 'PASS actual full16head attention calendar/realSRAM/RTLFP +3 mutations' > "$out/gate"
