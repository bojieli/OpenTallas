#!/bin/bash
# FUSED.QDQ WIDE throughput bench (tput-gate-1010): tb_hgi_quant_wide_tput (Verilator): m0 PASS; m1 (header A bit) and
# w1 (wide tag mutant) FAIL; w3 (forced packet path) PASS (control).
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
     rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/ot_hgi_quant_wide.sv rtl/hbm_accel/generic/ot_hgi_quant_unit.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     rtl/test/hbm_accel/generic/tb_hgi_quant_wide_tput.sv)
cfg=("m0:-GMUT=0 -GWMUT=0" "m1:-GMUT=1 -GWMUT=0" "w1:-GMUT=0 -GWMUT=1" "w3:-GMUT=0 -GWMUT=3")
for c in "${cfg[@]}"; do t=${c%%:*}; g=${c#*:}
  "$VL" --binary --timing -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style $g -GSERIAL_SHAPE=${SERIAL_SHAPE:-0} \
    --top-module tb_hgi_quant_wide_tput -Mdir "$out/$t.obj" -o sim "${src[@]}" > "$out/$t.build" 2>&1 &
done
wait
for c in "${cfg[@]}"; do t=${c%%:*}
  set +e; "$out/$t.obj/sim" +DIR="$vec" > "$out/$t.log" 2>&1; rc=$?; set -e; echo "$rc" > "$out/$t.rc"
done
ok=1
for t in m0 w3; do grep -q "PASS HGI_QDQ_WIDE_TPUT" "$out/$t.log" || ok=0; done
for t in m1 w1; do grep -q "PASS HGI_QDQ_WIDE_TPUT" "$out/$t.log" && ok=0; grep -qE "FATAL|MISMATCH" "$out/$t.log" || ok=0; done   # a mutant must FAIL in simulation, not in the build
[ $ok = 1 ] && echo "QDQ_WIDE_TPUT GATE PASS (m0/w3 PASS, m1/w1 FAIL)" | tee "$out/gate" || { echo "QDQ_WIDE_TPUT GATE FAIL" | tee "$out/gate"; exit 1; }
