#!/usr/bin/env bash
# C16 (HBMc/TILES2 10-22): lockstep ot_hidx_s3_flat (rs reference) vs ot_hidx_s3_flat_lpio (pin registers + OUTST output
# relays, outputs compared 1+OUTST edges later) on the lp.py selector programme; MUT 9 (in_line_1 register bypassed) and
# MUT 1 (landing 0 bypassed) must FAIL.  Exit 0 iff MUT 0 PASSES and every mutant FAILS.  usage: OUTDIR (OUTST=1|2)
set -u
cd "${LP_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}"
OUT=${1:-lpio_bench_out}; mkdir -p "$OUT"; rc=0; OUTST=${OUTST:-1}; FACE=${FACE:-0}
SRCS="rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_landing_native.sv rtl/hbm_accel/index/sel_s3/ot_hidx_s3_flat.sv rtl/hbm_accel/index/sel_s3/ot_hidx_s3_ctl.sv rtl/hbm_accel/index/sel_s3/ot_hidx_s3_q.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v rtl/common/landed_parent/ot_pl_land.sv rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lpio.sv rtl/hbm_accel/index/sel_s3/lp/tb_ot_hidx_s3_flat_lpio.sv"
for m in ${MUTS:-0 9 1}; do
  ${VERILATOR:-verilator} --binary -j ${VL_JOBS:-8} -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -O1 --top-module tb_ot_hidx_s3_flat_lpio -GMUT=$m -GOUTST=$OUTST -GFACE=$FACE $SRCS -Mdir "$OUT/obj$m" > "$OUT/build_$m.log" 2>&1 \
    && "$OUT/obj$m/Vtb_ot_hidx_s3_flat_lpio" > "$OUT/mut$m.log" 2>&1
  r=$(grep -o 'LP_LOCKSTEP [A-Z]*' "$OUT/mut$m.log" 2>/dev/null | head -1)
  echo "OUTST $OUTST FACE $FACE MUT $m: ${r:-NO_RESULT (see $OUT/build_$m.log)} $(grep -h -o 'LP_LOCKSTEP.*' "$OUT/mut$m.log" 2>/dev/null | head -1)"
  if [ $m -eq 0 ]; then [ "$r" = "LP_LOCKSTEP PASS" ] || rc=1; else [ "$r" = "LP_LOCKSTEP FAIL" ] || rc=1; fi
done
echo "BENCH_EXIT $rc"; exit $rc
