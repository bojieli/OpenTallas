#!/bin/bash
# OWNERS-HBM/QDQ 10-18: lockstep of ot_hgi_qdq_host_split (d4g split composition of the closed leaves) against the
# monolith ot_hgi_qdq_host_static #(RL7,WC4,COMPACT1) as GEN0 binds hb_quant_NW.  m0 positive (split = monolith,
# rq +1 edge, wq/done +5 edges, everything else same edge, golden writes on both); m1 = quant_NW0/1 write ports crossed
# (LGMUT=1); m2 = split RL=5 (LG/transport edges not priced).  Every mutant must fail with LOCKSTEP_FAIL.
set -euo pipefail
ulimit -c 0
out=$(realpath -m "$1"); mkdir -p "$out"
src=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv
 physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
 rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/lib/ot_rst_relay.sv
 rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_split.sv rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_r2.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_lg_port_group.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_split.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_record_calendar.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_host_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
 rtl/hbm_accel/generic/loader/ot_hgi_loader_cp.sv
 rtl/test/hbm_accel/generic/tb_hgi_qdq_host_split_lockstep.sv)
if [[ ${2:-} == --manifest ]]; then printf '%s\n' "${src[@]}"; exit; fi
for m in 0 1 2; do
 verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=$m \
  --top-module tb_hgi_qdq_host_split_lockstep -Mdir "$out/m$m.obj" -o sim "${src[@]}" > "$out/m$m.build" 2>&1 || { tail -30 "$out/m$m.build"; exit 1; }
 set +e; "$out/m$m.obj/sim" +DIR=tools/hgi_unit_tput/vectors/qdqvec +PROGRAM=results/hbm_static_quant_1015/compact_fixture.hex > "$out/m$m.log" 2>&1; rc=$?; set -e
 echo "$rc" > "$out/m$m.rc"
 if [[ $m == 0 ]]; then grep -q '^PASS HGI_QDQ_HOST_SPLIT_LOCKSTEP' "$out/m$m.log" || { tail -20 "$out/m$m.log"; exit 1; }
 else [[ $rc != 0 ]] || { echo "mutant $m survived"; exit 1; }; grep -q 'LOCKSTEP_FAIL' "$out/m$m.log" || { tail -5 "$out/m$m.log"; exit 1; }
 fi
 tail -2 "$out/m$m.log"
 rm -rf "$out/m$m.obj"
done
echo "PASS QDQ_HOST_SPLIT_LOCKSTEP_GATE m0 split==monolith (rq +1, wq/done +5) golden writes; mutants 1 2 killed (LOCKSTEP_FAIL)" | tee "$out/gate"
