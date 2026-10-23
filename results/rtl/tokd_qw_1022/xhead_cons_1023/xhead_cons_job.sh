#!/bin/bash
# TOKe-QW 10-23: per-consumer go_lag / xpf_lead sweep (o, down, qkv) + merge + the 4 cases and mutants with the merged ages.
# usage: xhead_cons_job.sh SRC OUT BUILD AGES0
set -u
SRC=$1; OUT=$2; BUILD=$3; A0=$4
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd "$SRC" || exit 9
mkdir -p "$OUT/pts" "$OUT/run"
verilator --version > "$OUT/verilator.version" 2>&1
B=rtl/test/qwen_dv/xhead_bench.py
sha256sum $B tools/qwen_layerbench/dv_lower_xhead.py tools/qwen_layerbench/dv_lower_vec.py tools/qwen_layerbench/dv_lower.py \
  rtl/test/qwen_dv/dv_lower_vec_bench.py rtl/test/qwen_dv/dv_lower_bench.py rtl/test/qwen_dv/dv_bench.py \
  rtl/test/qwen_dv/dv_bench2.py rtl/test/qwen_dv/tb_qfd_dv2.sv rtl/test/qwen_dv/main2.cpp rtl/qwen_dv/*.sv \
  rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv tools/qwen_layerbench/ctlm_image.py \
  results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex > "$OUT/source.sha256"
{
for c in o down; do for g in $(seq -6 12); do echo "$c $g 12"; done; for l in $(seq -2 8); do echo "$c 20 $l"; done; done
for g in $(seq -6 2); do echo "qkv $g 12"; done; for l in $(seq -1 6); do echo "qkv 20 $l"; done
} > "$OUT/points.txt"
xargs -P 24 -L 1 sh -c 'python3 '"$B"' --work '"$OUT"'/pts --build-dir '"$BUILD"' --ages '"$A0"' --point $0 --go-lag $1 --xpf-lead $2 > '"$OUT"'/pts/pt_$0_g$1_x$2.out 2>&1' < "$OUT/points.txt"
python3 $B --work "$OUT/pts" --ages "$A0" --merge "$OUT/xhead_ages.json" > "$OUT/merge.out" 2>&1; echo "rc=$?" >> "$OUT/merge.out"
A=$OUT/xhead_ages.json
[ -f "$A" ] || { echo "no merged ages"; exit 3; }
printf '%s\n' "gu -" "qkv -" "o -" "down -" "gu goearly" "gu xpflate" "gu isaxbase" "qkv goearly" "o goearly" "o xpflate" \
  "o isaxbase" "down goearly" "down xpflate" "down isaxbase" | xargs -P 14 -L 1 sh -c '
  if [ "$1" = - ]; then tag=$0_m0; ma=""; else tag=$0_$1; ma="--mutant $1"; fi
  python3 '"$B"' --work '"$OUT"'/run --build-dir '"$BUILD"' --run $0 $ma --ages '"$A"' > '"$OUT"'/$tag.out 2>&1; echo "rc=$?" >> '"$OUT"'/$tag.out'
cat "$OUT"/merge.out "$OUT"/*_m0.out "$OUT"/*_goearly.out "$OUT"/*_xpflate.out "$OUT"/*_isaxbase.out > "$OUT/bench.out" 2>/dev/null
exit 0
