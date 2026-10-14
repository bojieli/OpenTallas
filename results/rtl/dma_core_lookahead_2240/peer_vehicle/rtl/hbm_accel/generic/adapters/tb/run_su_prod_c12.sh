#!/usr/bin/env bash
# tput-fix-1011: the production-shape SU / SFU die-body bench (run_su_prod.sh, tb_hgi_su_prod) with the stream unit built
# as the die's c12 LANE ARRAY: the *_c12 lane / sfu / side / reducer / controller sources (the ones hfd_sfu's
# ot_su12_sfu lanes are built from) and ot_su13_ctl64's functional parameter set (-DOT_SU_C12 in ot_hgi_su_unit).
# usage: run_su_prod_c12.sh <outdir> [extra +define+ args...]   env as run_su_prod.sh (N M LV LWB UNIT WIDE MUT MUTW),
#   RSLICE (reducer slice lanes, default min(N, 64)), DENR (default 1), SFUT (default 0)
# The vectors (<outdir>/vec) are the same tools/hgi_unitrate/su_prod_vec.py output as run_su_prod.sh.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_su_prod_c12}"); shift || true
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"
[ -f "$OUT/vec/su_sizes.svh" ] || python3 "$ROOT/tools/hgi_unitrate/su_prod_vec.py" --out "$OUT/vec"
NN=${N:-64}; RS=${RSLICE:-$(( NN < 64 ? NN : 64 ))}
TAG="c12_n${NN}_m${M:-64}${UNIT:+_$UNIT}${WIDE:+_wide}${MUT:+_$MUT}${MUTW:+_mutw$MUTW}"
D="-DN=$NN -DM=${M:-64} -DLV=${LV:-7} -DLWB=${LWB:-18} -DOT_SU_C12 -DOT_SU_C12_RSLICE=$RS -DOT_SU_C12_DENR=${DENR:-1} -DOT_SU_C12_SFUT=${SFUT:-0}"
[ "${UNIT:-su}" = sfu ] && D="$D -DSFU"; [ -n "${WIDE:-}" ] && D="$D -DWIDE"; [ -n "${MUT:-}" ] && D="$D -D$MUT"; [ -n "${MUTW:-}" ] && D="$D -DMUT_W=$MUTW"
[ -n "${WDOG:-}" ] && D="$D -DWDOG=$WDOG"
L="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
   rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv
   rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv
   rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv
   rtl/hdc/v41/ot_hdc_fsqrt_c12.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv
   rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv
   rtl/hdc/v41x/ot_hdc_v41x_vec_red_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv
   rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
   rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/hbm_accel/generic/vm/ot_hgi_vm_lanearb.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_lanechain.sv
   physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   rtl/hbm_accel/generic/adapters/tb/tb_hgi_su_prod.sv"
cd "$ROOT"
"$VL" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  --top-module tb_hgi_su_prod -I"$OUT/vec" $D "$@" -Mdir "$OUT/obj_$TAG" $L -j ${JOBS:-16} > "$OUT/build_$TAG.log" 2>&1 \
  || { tail -30 "$OUT/build_$TAG.log"; exit 2; }
"$OUT/obj_$TAG/Vtb_hgi_su_prod" +DIR="$OUT/vec" | tee "$OUT/run_$TAG.log" | tail -25
