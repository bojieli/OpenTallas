#!/usr/bin/env bash
# L2H-SM9: ONE lockstep run of tb_ot_hbm_smh_rp4h2 (flat vs the two hardened halves) at MUT=$2 (0 = exact; 1..3 mutants), SOFTBEAT=$3 (default 0; 1 = kit smh_rp4hn_b soft beat).
# Fleet only (Verilator 5.050).  Prints "H2_LOCKSTEP PASS ..." / "H2_LOCKSTEP FAIL ..." and exits 0 on PASS, 1 otherwise.
#   bash rtl/hbm_accel/sm/repack/h2/run_rp4h2_one.sh OUTDIR MUT
set -u
cd "${LP_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/../../../../.." && pwd))}"
OUT=${1:-h2_one}; M=${2:-0}; SB=${3:-0}; mkdir -p "$OUT"
VERILATOR=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VERILATOR" --version
SRCS="rtl/hbm_accel/sm/repack/ot_hbm_smh_rp4_flat.sv rtl/lib/ot_hdly.sv rtl/hdc/ot_hdc_prefix.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_bterm2.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/gpu/ot_gpu_tree.sv rtl/gpu/ot_gpu_issue.sv rtl/gpu/ot_gpu_stack.sv rtl/gpu/ot_gpu_tc_col.sv rtl/gpu/ot_gpu_bd_col.sv rtl/hdc/v41/ot_hdc_blockdot.sv rtl/gpu/ot_gpu_bulk_copy.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq4.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq5.sv rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv rtl/hbm_accel/sm/ot_hbm_accel_stack.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv rtl/hbm_accel/sm/ot_hbm_accel_smh.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_cg.sv rtl/hbm_accel/cg/ot_cg_tile.sv rtl/hbm_accel/sm/ot_hbm_smh_compact_transport.sv rtl/hbm_accel/sm/ot_hbm_smh_transport_group_masters.sv rtl/hbm_accel/sm/ot_hbm_smh_transport_split_masters.sv rtl/hbm_accel/sm/ot_hbm_smh_transport_group.sv rtl/hbm_accel/sm/repack/ot_hbm_smh_rp4_clocks.sv rtl/hbm_accel/sm/repack/ot_rp4l_children.sv rtl/common/landed_parent/ot_pl_land.sv rtl/hbm_accel/sm/repack/h2/ot_hbm_smh_rp4h.sv rtl/hbm_accel/sm/repack/h2/tb_ot_hbm_smh_rp4h2.sv"
for t in 1 2; do
  "$VERILATOR" --binary -j 4 -Wno-fatal --top-module tb_ot_hbm_smh_rp4h2 -GMUT=$M -GSOFTBEAT=$SB -DOT_SMH_CG_ENREG -DOT_SMH_XLK -DOT_FP_DATA_NORST -DOT_SMH_DRST0 -DOT_SMH_RSTRELAY -DOT_SMH_RSTPIN -DOT_SMH_HIER -DOT_SMH_PTW_OHDLY -DOT_SMH_PINREG -DOT_SMH_XREL -DOT_SMH_PRODUCTION_SHAPE -DOT_SMH_COMPACT_PT -DOT_SMH_GROUP_TRANSPORT -DOT_SMH_WEST_SPLIT -DOT_SMH_TRANSPORT_KEEP -DOT_SMH_RP4_SRST $SRCS -Mdir "$OUT/obj" > "$OUT/build.log" 2>&1 && break
  sleep 5
done
"$OUT/obj/Vtb_ot_hbm_smh_rp4h2" | tee "$OUT/run.log"
rm -rf "$OUT/obj"
grep -q "^H2_LOCKSTEP PASS" "$OUT/run.log"
