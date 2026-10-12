#!/usr/bin/env bash
# hgi-unitrate: production-shape SU / SFU die-body bench (Verilator).
# usage: run_su_prod.sh <outdir> [extra +define+ args...]   env: N M LV LWB (defaults 64 64 7 18), UNIT=sfu, WIDE=1, MUT=MUT_DIRTY
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_su_prod}"); shift || true
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"
[ -f "$OUT/vec/su_sizes.svh" ] || python3 "$ROOT/tools/hgi_unitrate/su_prod_vec.py" --out "$OUT/vec"
TAG="n${N:-64}${UNIT:+_$UNIT}${WIDE:+_wide}${WIDE2:+_x}${MUTX:+_mutx$MUTX}${SHARED:+_shared}${CHAIN:+_chain}${ARBMUT:+_arbmut}${RLY:+_rly$RLY}${LQ:+_lq$LQ}${LRLAT:+_lat$LRLAT}${MUTRV:+_mutrv$MUTRV}${MUT:+_$MUT}${MUTW:+_mutw$MUTW}"
D="-DN=${N:-64} -DM=${M:-64} -DLV=${LV:-7} -DLWB=${LWB:-18}"
[ "${UNIT:-su}" = sfu ] && D="$D -DSFU"; [ -n "${WIDE:-}" ] && D="$D -DWIDE"; [ -n "${WIDE2:-}" ] && D="$D -DWIDE -DWIDE2"; [ -n "${MUTX:-}" ] && D="$D -DMUT_X=$MUTX"; [ -n "${XDBG:-}" ] && D="$D -DXDBG -DWDOG=20000"; [ -n "${SHARED:-}" ] && D="$D -DSHARED"; [ -n "${CHAIN:-}" ] && D="$D -DSHARED -DCHAIN"; [ -n "${ARBMUT:-}" ] && D="$D -DARBMUT"; [ -n "${RLY:-}" ] && D="$D -DRLY=$RLY"; [ -n "${LQ:-}" ] && D="$D -DLQ=$LQ"; [ -n "${LRLAT:-}" ] && D="$D -DLRLAT=$LRLAT"; [ -n "${MUTRV:-}" ] && D="$D -DMUT_RV=$MUTRV"; [ -n "${MUT:-}" ] && D="$D -D$MUT"; [ -n "${MUTW:-}" ] && D="$D -DMUT_W=$MUTW"
L="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
   rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv
   rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv
   rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv rtl/hdc/v41x/ot_hdc_v41x_vec.sv
   rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
   rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/hbm_accel/generic/vm/ot_hgi_vm_lanearb.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_lanechain.sv
   physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   rtl/hbm_accel/generic/adapters/tb/tb_hgi_su_prod.sv"
cd "$ROOT"
"$VL" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  --top-module tb_hgi_su_prod -I"$OUT/vec" $D "$@" -Mdir "$OUT/obj_$TAG" $L -j ${JOBS:-16} > "$OUT/build_$TAG.log" 2>&1 \
  || { tail -30 "$OUT/build_$TAG.log"; exit 2; }
"$OUT/obj_$TAG/Vtb_hgi_su_prod" +DIR="$OUT/vec" | tee "$OUT/run_$TAG.log" | tail -25
