#!/usr/bin/env bash
# L2H-SM9 (10-19): lockstep bench ot_hbm_smh_rp4_flat (flat, reset delayed 3) vs ot_hbm_smh_rp4h2 (the two hardened halves
# ot_hbm_smh_rp4h_n + ot_hbm_smh_rp4h_s abutted, lp offsets: gout +3, all else 0) + mutants 1..3 (each must FAIL).
# Run on the FLEET (ot-run), never on localhost.  Verilator = the closure daemon's 5.050.
#   bash rtl/hbm_accel/sm/repack/h2/ot_hbm_smh_rp4h2_bench.sh OUTDIR
set -u
cd "${LP_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../../../../.." && pwd))}"
OUT=${1:-h2_bench_out}; mkdir -p "$OUT"; rc=0
VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VERILATOR" --version > "$OUT/verilator_version.log" 2>&1; cat "$OUT/verilator_version.log"
SRCS="rtl/hbm_accel/sm/repack/ot_hbm_smh_rp4_flat.sv rtl/lib/ot_hdly.sv rtl/hdc/ot_hdc_prefix.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_bterm2.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/gpu/ot_gpu_tree.sv rtl/gpu/ot_gpu_issue.sv rtl/gpu/ot_gpu_stack.sv rtl/gpu/ot_gpu_tc_col.sv rtl/gpu/ot_gpu_bd_col.sv rtl/hdc/v41/ot_hdc_blockdot.sv rtl/gpu/ot_gpu_bulk_copy.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq4.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq5.sv rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv rtl/hbm_accel/sm/ot_hbm_accel_stack.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv rtl/hbm_accel/sm/ot_hbm_accel_smh.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_cg.sv rtl/hbm_accel/cg/ot_cg_tile.sv rtl/hbm_accel/sm/ot_hbm_smh_compact_transport.sv rtl/hbm_accel/sm/ot_hbm_smh_transport_group_masters.sv rtl/hbm_accel/sm/ot_hbm_smh_transport_split_masters.sv rtl/hbm_accel/sm/ot_hbm_smh_transport_group.sv rtl/hbm_accel/sm/repack/ot_hbm_smh_rp4_clocks.sv rtl/hbm_accel/sm/repack/ot_rp4l_children.sv rtl/common/landed_parent/ot_pl_land.sv rtl/hbm_accel/sm/repack/h2/ot_hbm_smh_rp4h.sv rtl/hbm_accel/sm/repack/h2/tb_ot_hbm_smh_rp4h2.sv"
run_m() {
  m=$1; sb=${2:-0}; tag=$m; [ "$sb" = 1 ] && tag=sb$m
  "$VERILATOR" --binary -j 8 -Wno-fatal --top-module tb_ot_hbm_smh_rp4h2 -GMUT=$m -GSOFTBEAT=$sb -DOT_SMH_CG_ENREG -DOT_SMH_XLK -DOT_FP_DATA_NORST -DOT_SMH_DRST0 -DOT_SMH_RSTRELAY -DOT_SMH_RSTPIN -DOT_SMH_HIER -DOT_SMH_PTW_OHDLY -DOT_SMH_PINREG -DOT_SMH_XREL -DOT_SMH_PRODUCTION_SHAPE -DOT_SMH_COMPACT_PT -DOT_SMH_GROUP_TRANSPORT -DOT_SMH_WEST_SPLIT -DOT_SMH_TRANSPORT_KEEP -DOT_SMH_RP4_SRST $SRCS -Mdir "$OUT/obj$tag" > "$OUT/build_$tag.log" 2>&1 \
    || { sleep 5; "$VERILATOR" --binary -j 8 -Wno-fatal --top-module tb_ot_hbm_smh_rp4h2 -GMUT=$m -GSOFTBEAT=$sb -DOT_SMH_CG_ENREG -DOT_SMH_XLK -DOT_FP_DATA_NORST -DOT_SMH_DRST0 -DOT_SMH_RSTRELAY -DOT_SMH_RSTPIN -DOT_SMH_HIER -DOT_SMH_PTW_OHDLY -DOT_SMH_PINREG -DOT_SMH_XREL -DOT_SMH_PRODUCTION_SHAPE -DOT_SMH_COMPACT_PT -DOT_SMH_GROUP_TRANSPORT -DOT_SMH_WEST_SPLIT -DOT_SMH_TRANSPORT_KEEP -DOT_SMH_RP4_SRST $SRCS -Mdir "$OUT/obj$tag" > "$OUT/build_$tag.retry.log" 2>&1; } \
    && "$OUT/obj$tag/Vtb_ot_hbm_smh_rp4h2" > "$OUT/mut$tag.log" 2>&1
  rm -rf "$OUT/obj$tag"
}
for m in 0 1 2 3; do run_m $m 0 & done; run_m 0 1 & run_m 1 1 & wait
for m in 0 1 2 3 sb0 sb1; do
  r=$(grep -o 'H2_LOCKSTEP [A-Z]*' "$OUT/mut$m.log" 2>/dev/null | head -1)
  echo "MUT $m: ${r:-NO_RESULT (see $OUT/build_$m.log)}"
  if [ $m = 0 ] || [ $m = sb0 ]; then [ "$r" = "H2_LOCKSTEP PASS" ] || rc=1; else [ "$r" = "H2_LOCKSTEP FAIL" ] || rc=1; fi
done
echo "BENCH_EXIT $rc"; exit $rc
