#!/bin/bash
set -euo pipefail
ulimit -c 0
out=$(realpath -m "$1");mkdir -p "$out"
for m in 0 1 2;do
 verilator --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style -GMUT=$m --top-module tb_hgi_qdq_record_calendar \
  -Mdir "$out/m$m.obj" -o sim rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_record_calendar.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  rtl/test/hbm_accel/generic/tb_hgi_qdq_record_calendar.sv > "$out/m$m.build" 2>&1
 set +e; "$out/m$m.obj/sim" > "$out/m$m.log" 2>&1;rc=$?;set -e
 if [[ $m == 0 ]];then grep -q '^PASS QUANT_RECORD_CALENDAR' "$out/m$m.log" || { cat "$out/m$m.log";exit 1; }
 else [[ $rc != 0 ]] || exit 1;grep -Eq 'record calendar fault|record command/cycle mismatch' "$out/m$m.log";fi
 cat "$out/m$m.log"
done
echo 'PASS QUANT_RECORD_CALENDAR_GATE exact mapped programme + wrong source/timestamp mutants killed' | tee "$out/gate"
