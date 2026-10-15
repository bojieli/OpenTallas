#!/bin/bash
set -euo pipefail
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
 rtl/test/hbm_accel/generic/tb_hgi_qdq_static.sv)
if [[ ${2:-} == --manifest ]]; then printf '%s\n' "${src[@]}"; exit; fi
for m in 0 1 2 3; do
 verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=$m -GIO_REGS=${IO_REGS:-0} --top-module tb_hgi_qdq_static \
  -Mdir "$out/m$m.obj" -o sim "${src[@]}" > "$out/m$m.build" 2>&1
 set +e; "$out/m$m.obj/sim" +DIR=tools/hgi_unit_tput/vectors/qdqvec +PROGRAM=results/hbm_static_quant_1015/program.hex > "$out/m$m.log" 2>&1; rc=$?;set -e
 echo "$rc" > "$out/m$m.rc"
 if [[ $m == 0 ]]; then grep -q '^PASS HGI_QDQ_STATIC' "$out/m$m.log" || { tail -20 "$out/m$m.log"; exit 1; }
 else
  [[ $rc != 0 ]] || { echo "mutant $m survived";exit 1; }
  case $m in
   1) grep -q 'gold mismatch' "$out/m$m.log";;
   2) grep -q 'unexpected bank write' "$out/m$m.log";;
   3) grep -q 'bad=1' "$out/m$m.log";;
  esac
 fi
 tail -3 "$out/m$m.log"
done
echo 'PASS STATIC_QUANT_GATE m0 exact production shape; m1 sector-map m2 write-map m3 late-response killed' | tee "$out/gate"
