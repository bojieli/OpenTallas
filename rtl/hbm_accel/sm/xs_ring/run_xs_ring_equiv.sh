#!/usr/bin/env bash
# HBM-SMHXS-RING: full-shape cycle equivalence; DUT ring versus legacy flop delay.
# usage: run_xs_ring_equiv.sh OUTDIR [MUT 0|1] [SEED] [CYCLES]   (run from the repo root; Verilator 5.050 preferred)
set -euo pipefail
OUT=$1; MUT=${2:-0}; SEED=${3:-1}; NC=${4:-3000}; FAN=${5:-0}; LOCAL=${6:-0}
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && PATH="$_d:$PATH"; done
mkdir -p "$OUT"; verilator --version
SRCS="rtl/hdc/ot_hdc_prefix.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_bterm2.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/gpu/ot_gpu_tree.sv rtl/gpu/ot_gpu_issue.sv rtl/gpu/ot_gpu_stack.sv rtl/gpu/ot_gpu_tc_col.sv rtl/gpu/ot_gpu_bd_col.sv rtl/hdc/v41/ot_hdc_blockdot.sv rtl/gpu/ot_gpu_bulk_copy.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq4.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq5.sv rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv rtl/hbm_accel/sm/ot_hbm_accel_stack.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv rtl/hbm_accel/sm/ot_hbm_accel_smh.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/lib/ot_hdly.sv rtl/lib/ot_rst_relay.sv"
# Both sides use identical E-face copies and two-edge reset landing; only DUT uses SRAM ring.
BASE="-DOT_SMH_XLK -DOT_FP_DATA_NORST -DOT_SMH_DRST0 -DOT_SMH_RSTRELAY -DOT_SMH_HIER -DOT_SMH_XSE -DOT_SMH_XSRST"
DUTD="$BASE -DOT_SMH_XSRING"; [ "$FAN" = 1 ] && DUTD="$DUTD -DOT_SMH_FAN32"; [ "$MUT" = 1 ] && DUTD="$DUTD -DOT_SMH_MUT_XSRING"
TBFL=();REFD="$BASE"
if [ "$LOCAL" = 1 ];then
 DUTD="$DUTD -DOT_SMH_RING_LOCAL_ADDR"; REFD="$BASE -DOT_SMH_XSRING -DOT_SMH_FAN32";TBFL=(-DOT_SMH_RING_LOCAL_CHECK)
fi
verilator -E -P $REFD $SRCS > "$OUT/ref_pp.sv"
sed -E 's/\bot_/ref_ot_/g' "$OUT/ref_pp.sv" > "$OUT/ref_ren.sv"
verilator -E -P $DUTD $SRCS > "$OUT/dut_pp.sv"
verilator --binary --timing -j 4 --top-module tb_xs_ring_equiv -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  "${TBFL[@]}" -DXSE_SEED=$SEED -DXSE_CYCLES=$NC --Mdir "$OUT/obj" -o vsim \
  "$OUT/dut_pp.sv" "$OUT/ref_ren.sv" rtl/hbm_accel/sm/xs_ring/tb_xs_ring_equiv.sv > "$OUT/build.log" 2>&1 || { tail -40 "$OUT/build.log"; echo "XS_RING_EQUIV BUILD_FAIL"; exit 2; }
"$OUT/obj/vsim" | tee "$OUT/run.log"
grep -q '^XS_RING_EQUIV PASS$' "$OUT/run.log"
