#!/usr/bin/env bash
# HBM-OWN/SMH2 r5: ONE lockstep run of tb_ot_hbm_smh_rp5_2 (rp4a flat vs the two REGIONAL landed attention halves) at
# VAR=$2 (0 MAIN x/c/m, 1 FB x/c), HMUT=$3 (0 exact; 1 xb crossing short, 2 gpm crossing short, 3 rl1 pad short,
# 5 n attn row off, 6 rl1 relay short), ATTN=$4 (default 13).  Kit shape GN 2 GS 2 XB 2 LR 2 OS 1 (gout tap 10 + DG).
# Fleet only (Verilator 5.050).  Prints "R5_LOCKSTEP PASS ..." / "R5_LOCKSTEP FAIL ..." and exits 0 on PASS, 1 otherwise.
#   bash rtl/hbm_accel/sm/repack/h2a5/run_rp5_2_one.sh OUTDIR VAR HMUT [ATTN]
set -u
cd "${LP_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../../../../.." && pwd))}"
OUT=${1:-r5_one}; VAR=${2:-0}; M=${3:-0}; AT=${4:-13}; mkdir -p "$OUT"
VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VERILATOR" --version
SRCS="rtl/lib/ot_hdly.sv rtl/hdc/ot_hdc_prefix.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_bterm2.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/gpu/ot_gpu_tree.sv rtl/gpu/ot_gpu_issue.sv rtl/gpu/ot_gpu_stack.sv rtl/gpu/ot_gpu_tc_col.sv rtl/gpu/ot_gpu_bd_col.sv rtl/hdc/v41/ot_hdc_blockdot.sv rtl/gpu/ot_gpu_bulk_copy.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq4.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq5.sv rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv rtl/hbm_accel/sm/ot_hbm_accel_stack.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv rtl/hbm_accel/sm/ot_hbm_accel_smh.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_gu.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir.v rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_cg.sv rtl/hbm_accel/cg/ot_cg_tile.sv rtl/hbm_accel/sm/ot_hbm_smh_compact_transport.sv rtl/hbm_accel/sm/ot_hbm_smh_transport_group_masters.sv rtl/hbm_accel/sm/ot_hbm_smh_transport_split_masters.sv rtl/hbm_accel/sm/ot_hbm_smh_transport_group.sv rtl/hbm_accel/sm/repack/ot_hbm_smh_rp4_clocks.sv rtl/hbm_accel/sm/repack/ot_rp4l_children.sv rtl/common/landed_parent/ot_pl_land.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge_s3.sv rtl/hbm_accel/sm/repack/h2/ot_hbm_smh_rp4h.sv rtl/hbm_accel/sm/repack/h2a/ot_hbm_smh_rp4ah.sv rtl/common/landed_parent/ot_pl_land_field_copies.sv rtl/common/landed_parent/ot_pl_land_reset_forest.sv rtl/hbm_accel/sm/repack/h2a5/ot_hbm_smh_rp5_soft.sv rtl/hbm_accel/sm/repack/h2a5/lp_n_m/ot_hbm_smh_rp5n_m.sv rtl/hbm_accel/sm/repack/h2a5/lp_n_f/ot_hbm_smh_rp5n_f.sv rtl/hbm_accel/sm/repack/h2a5/lp_s_m/ot_hbm_smh_rp5s_m.sv rtl/hbm_accel/sm/repack/h2a5/lp_s_f/ot_hbm_smh_rp5s_f.sv rtl/hbm_accel/sm/repack/h2a5/ot_hbm_smh_rp5_frame.sv rtl/hbm_accel/sm/repack/h2a5/tb_ot_hbm_smh_rp5_2.sv"
for t in 1 2; do
  "$VERILATOR" --binary -j 4 -Wno-fatal --top-module tb_ot_hbm_smh_rp5_2 -GVAR=$VAR -GHMUT=$M -GATTN=$AT -GGN=2 -GGS=2 -GXB=2 -GLR=2 -GOS=1 -DOT_SMH_CG_ENREG -DOT_SMH_XLK -DOT_FP_DATA_NORST -DOT_SMH_DRST0 -DOT_SMH_RSTRELAY -DOT_SMH_RSTPIN -DOT_SMH_HIER -DOT_SMH_PTW_OHDLY -DOT_SMH_PINREG -DOT_SMH_XREL -DOT_SMH_PRODUCTION_SHAPE -DOT_SMH_COMPACT_PT -DOT_SMH_GROUP_TRANSPORT -DOT_SMH_WEST_SPLIT -DOT_SMH_TRANSPORT_KEEP -DOT_SMH_RP4_SRST $SRCS -Mdir "$OUT/obj" > "$OUT/build.log" 2>&1 && break
  tail -30 "$OUT/build.log"
  sleep 5
done
"$OUT/obj/Vtb_ot_hbm_smh_rp5_2" | tee "$OUT/run.log"
rm -rf "$OUT/obj"
grep -q "^R5_LOCKSTEP PASS" "$OUT/run.log"
