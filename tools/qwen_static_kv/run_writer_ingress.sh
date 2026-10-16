#!/bin/bash
set -euo pipefail
OUT=${1:?output}; IMUT=${2:-0}; CASE=${3:-0}; WMUT=${4:-0}; mkdir -p "$OUT"
verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GIMUT="$IMUT" -GCASE="$CASE" -GWMUT="$WMUT" --top-module tb_qkd_static_writer_ingress -Mdir "$OUT/obj_${IMUT}_${CASE}_${WMUT}" \
 rtl/test/qwen_static_kv/tb_qkd_static_writer_ingress.sv rtl/qwen_sys/static_kv_20261014/qkd_static_writer_ingress.sv \
 rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv rtl/physical/ot_qkd_kv_static_writer_native.sv \
 rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv rtl/lib/ot_rst_relay.sv > "$OUT/build_${IMUT}_${CASE}_${WMUT}.log" 2>&1
python3 - "$OUT/boot.hex" <<'PY'
import sys
with open(sys.argv[1],'w')as f:
 for l in range(36):
  for x in (4,5,6,7,10):f.write(f'{x:016x}\n')
 f.write('514b565052473336\n')
PY
cd "$OUT"
set +e
"$OUT/obj_${IMUT}_${CASE}_${WMUT}/Vtb_qkd_static_writer_ingress" > "$OUT/run_${IMUT}_${CASE}_${WMUT}.log" 2>&1
result=$?
set -e
cat "$OUT/run_${IMUT}_${CASE}_${WMUT}.log"
exit "$result"
