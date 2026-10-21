#!/usr/bin/env bash
# LH-SMATT/XS 10-19: production-shape (full ot_hbm_accel_smh_xs, all 1615 output bits every cycle, async reset bursts)
# equivalence of the two SAFE ring successors against (a) the rg2 SRAM ring (plus per-macro read/write address checks)
# and (b) the legacy r0w/w3/w3b flop pipeline.
# usage: run_xs_ring_safe.sh OUTDIR VARIANT(A|B) REF(ring|legacy) MUT(0|r|w) [SEED] [CYCLES]   (repo root; Verilator 5.050)
#   A = 4 x 128x256 ring + macro-local posedge read/write address captures + own ring reset relay
#   B = A with the ring on 7 x ot_sram_1r1w_32x128_m1
#   C = B on the wide-pitch p192 macro variants (OT_SMH_SRAM_P192; ring 32x128_p192_rc, x store 128x256_r2c2_p192_mir)
#   MUT r = read-slot mutant (OT_SMH_MUT_XSRING), w = write-slot mutant (OT_SMH_MUT_XSRING_W); both must FAIL.
set -euo pipefail
OUT=$1; VAR=$2; REF=$3; MUT=$4; SEED=${5:-1}; NC=${6:-3000}
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && PATH="$_d:$PATH"; done
mkdir -p "$OUT"; verilator --version
SRCS="rtl/hdc/ot_hdc_prefix.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_bterm2.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/gpu/ot_gpu_tree.sv rtl/gpu/ot_gpu_issue.sv rtl/gpu/ot_gpu_stack.sv rtl/gpu/ot_gpu_tc_col.sv rtl/gpu/ot_gpu_bd_col.sv rtl/hdc/v41/ot_hdc_blockdot.sv rtl/gpu/ot_gpu_bulk_copy.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq4.sv rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq5.sv rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv rtl/hbm_accel/sm/ot_hbm_accel_stack.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv rtl/hbm_accel/sm/ot_hbm_accel_smh.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/lib/ot_hdly.sv rtl/lib/ot_rst_relay.sv"
BASE="-DOT_SMH_XLK -DOT_FP_DATA_NORST -DOT_SMH_DRST0 -DOT_SMH_RSTRELAY -DOT_SMH_HIER -DOT_SMH_XSE -DOT_SMH_XSRST"
DUTD="$BASE -DOT_SMH_XSRING -DOT_SMH_FAN32 -DOT_SMH_RING_LOCAL_ADDR -DOT_SMH_RING_LOCAL_WADDR -DOT_SMH_RING_RST2"; NRG=4
[ "$VAR" = B ] && { DUTD="$DUTD -DOT_SMH_XSRING32"; NRG=7; }
[ "$VAR" = C ] && { DUTD="$DUTD -DOT_SMH_XSRING32 -DOT_SMH_SRAM_P192"; NRG=7; SRCS="$SRCS physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir.v physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v"; }
[ "$MUT" = r ] && DUTD="$DUTD -DOT_SMH_MUT_XSRING"
[ "$MUT" = w ] && DUTD="$DUTD -DOT_SMH_MUT_XSRING_W"
TBFL=(-DXSE_NRG=$NRG)
if [ "$REF" = ring ]; then REFD="$BASE -DOT_SMH_XSRING -DOT_SMH_FAN32"; TBFL+=(-DOT_SMH_RING_LOCAL_CHECK); else REFD="$BASE"; fi
echo "XS_RING_SAFE variant=$VAR ref=$REF mut=$MUT seed=$SEED cycles=$NC"; echo "DUT $DUTD"; echo "REF $REFD"
verilator -E -P $REFD $SRCS > "$OUT/ref_pp.sv"
sed -E 's/\bot_/ref_ot_/g' "$OUT/ref_pp.sv" > "$OUT/ref_ren.sv"
verilator -E -P $DUTD $SRCS > "$OUT/dut_pp.sv"
verilator --binary --timing -j 4 --top-module tb_xs_ring_equiv -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  "${TBFL[@]}" -DXSE_SEED=$SEED -DXSE_CYCLES=$NC --Mdir "$OUT/obj" -o vsim \
  "$OUT/dut_pp.sv" "$OUT/ref_ren.sv" rtl/hbm_accel/sm/xs_ring/tb_xs_ring_equiv.sv > "$OUT/build.log" 2>&1 || { tail -40 "$OUT/build.log"; echo "XS_RING_EQUIV BUILD_FAIL"; exit 2; }
"$OUT/obj/vsim" | tee "$OUT/run.log"
grep -q '^XS_RING_EQUIV PASS$' "$OUT/run.log"
