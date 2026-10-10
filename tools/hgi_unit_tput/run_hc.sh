#!/bin/bash
# HC unit throughput bench (hgi-1010/g): tools/hgi_unit_tput/run_hc.sh <vectors dir> <out dir>   (from the repo root)
# builds tb_hgi_hc_tput (Verilator) twice: PASS build and +define+MUT_POST (must FAIL); env FA (HBM first access).
set -euo pipefail
vec=$(realpath "$1"); out=$(realpath -m "$2"); mkdir -p "$out"
VL=${VERILATOR:-verilator}
SRC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv
  rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv
  rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv
  rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sinkhorn_mc.sv
  rtl/hbm_accel/generic/adapters/ot_hgi_hc_record.sv rtl/hbm_accel/generic/peers/ot_hgi_hc_unit.sv
  rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
for m in pass MUT_POST; do
  D=""; [ $m != pass ] && D="+define+$m"
  "$VL" --binary --timing -O3 -CFLAGS -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN $D \
    --top-module tb_hgi_hc_tput -I"$vec" -Mdir "$out/$m.obj" $SRC rtl/hbm_accel/generic/adapters/tb/tb_hgi_hc_tput.sv \
    -j 8 > "$out/$m.build" 2>&1 &
done
wait
for m in pass MUT_POST; do "$out/$m.obj/Vtb_hgi_hc_tput" +DIR="$vec" +FA=${FA:-160} > "$out/$m.log" 2>&1 || true; done
if grep -q "HGI_HC_TPUT PASS" "$out/pass.log" && ! grep -q "HGI_HC_TPUT PASS" "$out/MUT_POST.log"; then
  echo "HC_TPUT GATE PASS (pass PASS, MUT_POST FAIL)" | tee "$out/gate"; else echo "HC_TPUT GATE FAIL" | tee "$out/gate"; exit 1; fi
