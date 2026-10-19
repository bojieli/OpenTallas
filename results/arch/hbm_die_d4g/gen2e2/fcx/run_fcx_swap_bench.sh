#!/usr/bin/env bash
# LH-GEN2E-IN 10-19: bench of the fc_xr2 swap in the d4g die SM master (ot_smh_static_front u_rw / u_re = fc_xr2 r4,
# ot_hbm_accel_smh_attn FCX_EDGE tile-row-0 gather landing, compiler fcx_edge = +1 in sm_elem_bench.py).
# Verilator 5.050 (the closure daemon's), fleet only.  Three ot-run jobs in parallel, each with its own build dir:
#   pos   ds640 all + ds128 all (every op exact, default calendar with fcx_edge 1)  -> PASS
#         tight  ds640 qk_sm0 (publish = measured last landing + edge + 1)         -> PASS
#         fcx0   ds640 qk_sm0 (the tight calendar WITHOUT the +1 edge)              -> FAIL (offset-wrong compiler mutant)
#         early  ds640 qk_sm0 (existing r8 negative control)                        -> FAIL
#   mut   OT_SMH_FCX_MUT_NOALIGN (fc_xr2 without the gather landing) ds640 qk_sm0,pv_sm0 -> FAIL (offset-wrong RTL mutant)
#   cal   PROBE build, qk_sm0, calibrate -> measured QK landing window (expect qk_first 64 / qk_land_meas 71 = r8 + 1)
# usage: run_fcx_swap_bench.sh REV [HOST] [OUT]
set -uo pipefail
REV=$1; HOST=${2:-ot-epyc5}; OUT=${3:-/srv/opentallas-scratch/claude/lh-gen2e-in/fcx_bench}
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator HDC_V41_ARITH=chunk8'
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "mkdir -p $OUT/src $OUT/out && rm -rf $OUT/src/*" || exit 2
git -C "$WT" archive "$SHA" tools/hbm_sm_attention tools/hgi_sim tools/hdc_golden_v41.py tools/hdc_golden.py tools/hdc_isa.py rtl/hdc rtl/gpu \
  rtl/proto rtl/lib rtl/v41rom rtl/hbm_accel/sm rtl/hbm_accel/epilogue rtl/test/hbm_accel/sm_attn \
  physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  | ssh "$HOST" "tar -x -C $OUT/src" || exit 2
echo "$SHA" | ssh "$HOST" "cat > $OUT/src/REV"
E="cd $OUT/src && $VL python3 tools/hbm_sm_attention/sm_elem_bench.py"
R=/home/ubuntu/bin/ot-run
$R --mem 32 --threads 16 --dir "$OUT" -- bash -c "\
  $E run --shape ds640 --ops all --work $OUT/wpos --out $OUT/out/ds640_all.json > $OUT/out/ds640_all.log 2>&1; echo ds640_all rc=\$?; \
  $E run --shape ds128 --ops all --work $OUT/wpos --out $OUT/out/ds128_all.json > $OUT/out/ds128_all.log 2>&1; echo ds128_all rc=\$?; \
  for m in tight fcx0 early; do $E run --shape ds640 --ops qk_sm0 --smut \$m --work $OUT/wpos --out $OUT/out/ds640_\$m.json \
    > $OUT/out/ds640_\$m.log 2>&1; echo ds640_\$m rc=\$?; done" > /tmp/lhgen2ein_fcx_pos.out 2>&1 &
P1=$!
$R --mem 32 --threads 16 --dir "$OUT" -- bash -c "\
  $E run --shape ds640 --ops qk_sm0,pv_sm0 --define OT_SMH_FCX_MUT_NOALIGN --work $OUT/wmut --out $OUT/out/ds640_noalign.json \
    > $OUT/out/ds640_noalign.log 2>&1; echo ds640_noalign rc=\$?" > /tmp/lhgen2ein_fcx_mut.out 2>&1 &
P2=$!
$R --mem 32 --threads 16 --dir "$OUT" -- bash -c "\
  $E run --shape ds640 --ops qk_sm0 --probe --work $OUT/wcal --out $OUT/out/ds640_probe.json > $OUT/out/ds640_probe.log 2>&1; echo probe rc=\$?; \
  $E calibrate --shape ds640 --op qk_sm0 --probe-dir $OUT/wcal/ds640_qk_sm0_p1_d0 --out $OUT/out/qk_landing_calibration.json \
    > $OUT/out/calibrate.log 2>&1; echo calibrate rc=\$?" > /tmp/lhgen2ein_fcx_cal.out 2>&1 &
P3=$!
wait $P1 $P2 $P3
echo FCX_SWAP_BENCH_DONE
