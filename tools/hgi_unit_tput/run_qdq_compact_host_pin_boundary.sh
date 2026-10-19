#!/bin/bash
# HBMA-QDQ 10-17: exact production-shape gate of ot_hgi_qdq_host_static (COMPACT1, target48, RL7/WC4 as the d4f die binds)
# on the current native NW slice (RG5/WG3), with the opt-in physical pin boundary.  IO_REGS / PIN_BOUNDARY from the env
# (default 1/1 = the hardened tile).  m0 positive; m1..m6 the original six mutants; m7 (IO_REGS=1 only) = the IO_REGS=0
# VM programme (write reservation t+35) against the registered boundary: must fail on the bank write slot.
set -euo pipefail
ulimit -c 0
out=$(realpath -m "$1"); mkdir -p "$out"
IO=${IO_REGS:-1}; PB=${PIN_BOUNDARY:-1}
src=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv
 physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
 rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/lib/ot_rst_relay.sv
 rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_program_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_record_calendar.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_host_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
 rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_static.sv
 rtl/hbm_accel/generic/loader/ot_hgi_loader_cp.sv
 rtl/test/hbm_accel/generic/tb_hgi_qdq_compact_host_pin_boundary.sv)
if [[ ${2:-} == --manifest ]]; then printf '%s\n' "${src[@]}"; exit; fi
P=results/hbm_static_quant_1015/nw_pin_boundary
muts="0 1 2 3 4 5 6"; [[ $IO == 1 ]] && muts="$muts 7"
for m in $muts; do
 vm=$P/nw_compact_program_rg5_io$IO.hex; dm=$m; [[ $m == 7 ]] && { vm=$P/nw_compact_program_rg5_io0.hex; dm=0; }
 verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=$dm -GIO_REGS=$IO -GPIN_BOUNDARY=$PB \
  --top-module tb_hgi_qdq_compact_host_pin_boundary -Mdir "$out/m$m.obj" -o sim "${src[@]}" > "$out/m$m.build" 2>&1
 set +e; "$out/m$m.obj/sim" +DIR=tools/hgi_unit_tput/vectors/qdqvec +PROGRAM=results/hbm_static_quant_1015/compact_fixture.hex +VM_PROGRAM=$vm > "$out/m$m.log" 2>&1; rc=$?;set -e
 echo "$rc" > "$out/m$m.rc"
 if [[ $m == 0 ]]; then grep -q '^PASS HGI_QDQ_COMPACT_PIN_BOUNDARY_NW' "$out/m$m.log" || { tail -20 "$out/m$m.log"; exit 1; }
 else
  [[ $rc != 0 ]] || { echo "mutant $m survived";exit 1; }
  case $m in
   1) grep -q 'gold mismatch' "$out/m$m.log";;
   2) grep -q 'unexpected bank write' "$out/m$m.log";;
   3) grep -q 'bad=1' "$out/m$m.log";;
   4) grep -Eq 'bank fault|fixed done differs' "$out/m$m.log";;
   5) grep -q 'native fixed completion missing' "$out/m$m.log";;
   6) grep -q 'unexpected static fault' "$out/m$m.log";;
   7) grep -Eq 'bank fault|fixed done differs|unexpected bank write' "$out/m$m.log";;
  esac
 fi
 tail -3 "$out/m$m.log"
done
echo "PASS STATIC_QUANT_PIN_BOUNDARY_NW_GATE IO_REGS=$IO PIN_BOUNDARY=$PB m0 exact production shape actual loader CP and current RG5 NW slice; mutants $muts killed" | tee "$out/gate"
