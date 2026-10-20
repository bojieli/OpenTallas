#!/bin/bash
# QLB-C4b/3a: build tb_qfd_dv2 N 12 once (Verilator 5.050), calibrate, then every mode m0 + its mutants.
set -u
SRC=$1; OUT=$2
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd "$SRC" || exit 9
W=$OUT/work; mkdir -p "$W"
verilator --version > "$OUT/verilator.version" 2>&1
sha256sum tools/qwen_layerbench/dv_lower_vec.py tools/qwen_layerbench/dv_lower.py rtl/test/qwen_dv/dv_lower_vec_bench.py \
  rtl/test/qwen_dv/dv_lower_bench.py rtl/test/qwen_dv/dv_bench.py rtl/test/qwen_dv/dv_bench2.py rtl/test/qwen_dv/tb_qfd_dv2.sv \
  rtl/test/qwen_dv/main2.cpp rtl/qwen_dv/*.sv tools/hdc_golden.py tools/hdc_qwen_fullshape_isa_w12.py tools/hdc_isa.py \
  results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex \
  results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/token_source_plan.json \
  results/arch/qwen_split_compute_1014/dieplan2_1016/dv2r8f7r_qdv_p2462.json \
  results/rtl/qlb_gen_1018/dv2f14bq/relay_stages_compute.json > "$OUT/source.sha256"
B=rtl/test/qwen_dv/dv_lower_vec_bench.py
python3 $B --work "$W" --mode calibrate > "$OUT/calibrate.out" 2>&1; echo "rc=$?" >> "$OUT/calibrate.out"
cp "$W/vec_ages.json" "$OUT/" 2>/dev/null
for spec in "resid -" "qk -" "silu -" "resid arwin" "resid xslot" "qk ropesign" "silu nor"; do
  set -- $spec; m=$1; mu=$2
  if [ "$mu" = - ]; then tag=${m}_m0; ma=""; else tag=${m}_$mu; ma="--mutant $mu"; fi
  python3 $B --work "$W" --mode $m $ma --ages "$W/vec_ages.json" > "$OUT/$tag.out" 2>&1; echo "rc=$?" >> "$OUT/$tag.out"
done
cat "$OUT"/*.out > "$OUT/bench.out"
exit 0
