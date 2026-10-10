#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
hdc=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv)
src=("${hdc[@]}" physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/hbm_accel/generic/ot_hgi_quant_vm_transport.sv rtl/hbm_accel/generic/ot_hgi_quant_record.sv rtl/test/hbm_accel/generic/tb_hgi_quant_vm_transport.sv)
for mutant in 0 1 2 3;do
 verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -DMUTANT=$mutant --top-module tb_hgi_quant_vm_transport -Mdir "$out/m$mutant.obj" -o sim "${src[@]}" > "$out/m$mutant.build" 2>&1
 set +e
 "$out/m$mutant.obj/sim" +VECTORS=results/hgi_generic/cf_qdq_891b4b555 > "$out/m$mutant.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$out/m$mutant.rc"
 if [[ $mutant == 0 ]];then [[ $rc == 0 ]];grep -q 'PASS QUANT_TRANSPORT' "$out/m$mutant.log";else [[ $rc != 0 ]];grep -Eq 'WRITE mismatch|DROP/CREDIT|EARLY_DONE' "$out/m$mutant.log";fi
done
