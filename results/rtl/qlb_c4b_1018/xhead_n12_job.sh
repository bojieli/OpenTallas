#!/bin/bash
# QW-XHEAD 10-19: x-consumer lowering bench on tb_qfd_dv2 N 12 (+DV2_XHEAD), Verilator 5.050.
# usage: xhead_n12_job.sh SRC OUT    (SRC = staged source tree; OUT = run directory)
set -u
SRC=$1; OUT=$2
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd "$SRC" || exit 9
mkdir -p "$OUT"
verilator --version > "$OUT/verilator.version" 2>&1
B=rtl/test/qwen_dv/xhead_bench.py
sha256sum $B tools/qwen_layerbench/dv_lower_xhead.py tools/qwen_layerbench/dv_lower_vec.py tools/qwen_layerbench/dv_lower.py \
  rtl/test/qwen_dv/dv_lower_vec_bench.py rtl/test/qwen_dv/dv_lower_bench.py rtl/test/qwen_dv/dv_bench.py \
  rtl/test/qwen_dv/dv_bench2.py rtl/test/qwen_dv/tb_qfd_dv2.sv rtl/test/qwen_dv/main2.cpp rtl/qwen_dv/*.sv \
  rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv tools/qwen_layerbench/ctlm_image.py \
  results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex > "$OUT/source.sha256"
python3 $B --work "$OUT/cal" --build-dir "$OUT" --calibrate > "$OUT/calibrate.out" 2>&1; echo "rc=$?" >> "$OUT/calibrate.out"
A=$OUT/cal/xhead_ages.json
[ -f "$A" ] || { echo "no ages"; exit 3; }
for spec in "gu -" "qkv -" "o -" "down -" "gu goearly" "gu xpflate" "gu isaxbase" "o goearly" "down xpflate"; do
  set -- $spec; c=$1; mu=$2
  if [ "$mu" = - ]; then tag=${c}_m0; ma=""; else tag=${c}_$mu; ma="--mutant $mu"; fi
  python3 $B --work "$OUT/run" --build-dir "$OUT" --run $c $ma --ages "$A" > "$OUT/$tag.out" 2>&1; echo "rc=$?" >> "$OUT/$tag.out"
done
cat "$OUT"/calibrate.out "$OUT"/*_m0.out "$OUT"/*_goearly.out "$OUT"/*_xpflate.out "$OUT"/*_isaxbase.out > "$OUT/bench.out" 2>/dev/null
exit 0
