#!/usr/bin/env bash
# hgi-adapters: stub-consumer bench of one record adapter.  usage: run_small.sh <unit: sm|dma|att|hc|argmax> <outdir> [MUT_*]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
U=$1; OUT=$(realpath -m "${2:-/tmp/hgi_${1}_run}"); MUT=${3:-}
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
python3 tools/hgi_adapters/${U}_bench.py --out "$OUT/vec" > "$OUT/gen.log"
VEC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
   rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv
   rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv
   rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv rtl/hdc/v41x/ot_hdc_v41x_vec.sv"
case $U in
  mover) SRC="rtl/hbm_accel/generic/adapters/ot_hgi_dma_record.sv rtl/hbm_accel/generic/peers/ot_hgi_dma_mover.sv
     rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" ;;
  att) SRC="rtl/hbm_accel/generic/adapters/ot_hgi_att_issue.sv" ;;
  fused) SRC="rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv rtl/hbm_accel/generic/adapters/ot_hgi_fused_record.sv $VEC" ;;
  *)   SRC="rtl/hbm_accel/generic/adapters/ot_hgi_${U}_record.sv" ;;
esac
EXTRA=${EXTRA_SRC:-}
# argmax: the real engine (ot_hgi_argmax18_m GENERIC18 1) and the real HGI VM (ot_hgi_vm_unit / core + macro models)
[ "$U" = argmax ] && EXTRA="$EXTRA physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv
  physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
  rtl/gpu/ot_gpu_fadd.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
D=""; [ -n "$MUT" ] && D="-D$MUT"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN --top-module tb_hgi_${U}_record \
  -I"$OUT/vec" $D -Mdir "$OUT/obj${MUT:+_$MUT}" $SRC $EXTRA rtl/hbm_accel/generic/adapters/tb/tb_hgi_${U}_record.sv -j ${J:-16} \
  > "$OUT/build${MUT:+_$MUT}.log" 2>&1 || { rm -f "$OUT/run${MUT:+_$MUT}.log"; tail -30 "$OUT/build${MUT:+_$MUT}.log"; exit 2; }
"$OUT/obj${MUT:+_$MUT}/Vtb_hgi_${U}_record" +DIR="$OUT/vec" | tee "$OUT/run${MUT:+_$MUT}.log" | tail -8
