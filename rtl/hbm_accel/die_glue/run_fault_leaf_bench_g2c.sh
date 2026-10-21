#!/usr/bin/env bash
# IDLE-STANDIN 2026-10-19 (copy of run_fault_leaf_bench.sh for the GEN2c wrappers): ot_hbm_fault_leaf unit bench at one die parameter set (Icarus).
#   run_fault_leaf_bench_g2c.sh OUTDIR N SYNC_MASK_HEX MUT [WRAP]     e.g. run_fault_leaf_bench.sh out 5 8 0
#   WRAP=1: bench the per-variant wrapper block ot_hbm_fault_leaf_n<N>_s<mask> (ot_hbm_fault_leaf_variants_g2c.sv)
# MUT 0 must print PASS (exit 0); MUT 1 (drops in[N-1]) / 2 (unregistered output) / 3 (SYNC_MASK ignored, only when the
# mask is non-zero) must print FAIL (exit 1).
set -u
out=${1:?outdir}; n=${2:?N}; sm=${3:?SYNC_MASK hex}; mut=${4:-0}; wrap=${5:-0}
mkdir -p "$out"; R=$(cd "$(dirname "$0")/../../.." && pwd); D=$R/rtl/hbm_accel/die_glue
tag="n${n}_s${sm}_m${mut}"; [ "$wrap" = 0 ] || tag="w_$tag"
sha256sum "$D/tb_hbm_fault_leaf_g2c.sv" "$D/ot_hbm_fault_leaf.sv" "$D/ot_hbm_fault_leaf_variants_g2c.sv" > "$out/$tag.source.sha256"
iverilog -g2012 -s tb_hbm_fault_leaf_g2c -Ptb_hbm_fault_leaf_g2c.N="$n" -Ptb_hbm_fault_leaf_g2c.SYNC_MASK="64'h$sm" \
  -Ptb_hbm_fault_leaf_g2c.MUT="$mut" -Ptb_hbm_fault_leaf_g2c.WRAP="$wrap" -o "$out/$tag.vvp" "$D/tb_hbm_fault_leaf_g2c.sv" "$D/ot_hbm_fault_leaf.sv" "$D/ot_hbm_fault_leaf_variants_g2c.sv" \
  > "$out/$tag.build.log" 2>&1 || { echo "BUILD_FAIL $tag"; cat "$out/$tag.build.log"; exit 2; }
vvp -n "$out/$tag.vvp" > "$out/$tag.log" 2>&1; rc=$?
cat "$out/$tag.log"
grep -q '^PASS tb_hbm_fault_leaf' "$out/$tag.log" && [ "$rc" = 0 ] && { echo "FAULT_LEAF_BENCH PASS $tag"; exit 0; }
echo "FAULT_LEAF_BENCH FAIL $tag rc=$rc"; exit 1
