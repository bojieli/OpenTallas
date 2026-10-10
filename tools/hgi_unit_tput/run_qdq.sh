#!/bin/bash
# FUSED.QDQ throughput bench (hgi-1010/g): build tb_hgi_quant_tput (Verilator) and run PASS + mutants.
# usage (from the repo root): tools/hgi_unit_tput/run_qdq.sh <vectors dir> <out dir>
# env: SERIAL_SHAPE (0|1), VERILATOR
set -euo pipefail
vec=$(realpath "$1"); out=$(realpath -m "$2"); mkdir -p "$out"
VL=${VERILATOR:-verilator}
hdc=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
     rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv)
src=("${hdc[@]}" physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
     rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv
     rtl/hbm_accel/generic/ot_hgi_quant_vm_transport.sv rtl/hbm_accel/generic/ot_hgi_quant_record.sv
     rtl/hbm_accel/generic/ot_hgi_quant_unit.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     rtl/test/hbm_accel/generic/tb_hgi_quant_tput.sv)
for m in 0 1 2; do
  "$VL" --binary --timing -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=$m -GSERIAL_SHAPE=${SERIAL_SHAPE:-0} \
    --top-module tb_hgi_quant_tput -Mdir "$out/m$m.obj" -o sim "${src[@]}" > "$out/m$m.build" 2>&1 &
done
wait
for m in 0 1 2; do
  set +e; "$out/m$m.obj/sim" +DIR="$vec" > "$out/m$m.log" 2>&1; rc=$?; set -e
  echo "$rc" > "$out/m$m.rc"
done
ok=1
grep -q "PASS HGI_QDQ_TPUT" "$out/m0.log" || ok=0
for m in 1 2; do grep -q "PASS HGI_QDQ_TPUT" "$out/m$m.log" && ok=0; done
[ $ok = 1 ] && echo "QDQ_TPUT GATE PASS (m0 PASS, m1/m2 FAIL)" | tee "$out/gate" || { echo "QDQ_TPUT GATE FAIL" | tee "$out/gate"; exit 1; }
