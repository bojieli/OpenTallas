#!/bin/bash
set -euo pipefail
ulimit -c 0
out=$(realpath -m "$1"); mkdir -p "$out"
src=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv
 physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
 rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/lib/ot_rst_relay.sv
 rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_program_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_sw_host_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_record_calendar.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_host_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
 rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_static.sv
 rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_SW_quant.sv
 rtl/hbm_accel/generic/loader/ot_hgi_loader_cp.sv
 rtl/test/hbm_accel/generic/tb_hgi_qdq_sw_host_static.sv)
if [[ ${2:-} == --manifest ]]; then printf '%s\n' "${src[@]}"; exit; fi
for m in 0 1 2 3 4 5 6; do
 verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=$m -GIO_REGS=${IO_REGS:-0} -GPIN_BOUNDARY=${PIN_BOUNDARY:-0} --top-module tb_hgi_qdq_sw_host_static \
  -Mdir "$out/m$m.obj" -o sim "${src[@]}" > "$out/m$m.build" 2>&1
 set +e; "$out/m$m.obj/sim" +DIR=results/hbm_static_quant_1015/SW_replica/vectors +PROGRAM=results/hbm_static_quant_1015/SW_replica/program.hex +VM_PROGRAM=${VM_PROGRAM:-results/hbm_static_quant_1015/SW_replica/SW_program.hex} > "$out/m$m.log" 2>&1; rc=$?;set -e
 echo "$rc" > "$out/m$m.rc"
 if [[ $m == 0 ]]; then grep -q '^PASS HGI_QDQ_SW_TARGET125_NATIVE_HOST' "$out/m$m.log" || { tail -20 "$out/m$m.log"; exit 1; }
 else
  [[ $rc != 0 ]] || { echo "mutant $m survived";exit 1; }
  case $m in
   1) grep -q 'gold mismatch' "$out/m$m.log";;
   2) grep -q 'unexpected bank write' "$out/m$m.log";;
   3) grep -q 'bad=1' "$out/m$m.log";;
   4) grep -Eq 'bank fault|fixed done differs' "$out/m$m.log";;
   5) grep -q 'native fixed completion missing' "$out/m$m.log";;
   6) grep -q 'unexpected static fault' "$out/m$m.log";;
  esac
 fi
 tail -3 "$out/m$m.log"
done
echo 'PASS STATIC_QUANT_SW125_NATIVE_HOST_GATE m0 exact production shape actual loader CP and NW calendar; m1/m2/m3/m4/m5/m6 killed' | tee "$out/gate"
