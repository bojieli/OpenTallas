#!/bin/bash
# HBM-P4-QUANT 10-23 (COORD R6(3)): lockstep of the replicated quadrant QUANT + VM write-merge group ot_hbm_quant_vmm_q
# against the golden monolith ot_hgi_qdq_host_static (qdqvec records, golden output sectors), one run per quadrant.
#   q0..q3  positive, Q = 0 NW / 1 NE / 2 SW / 3 SE, L 54 (the die RL at hb_quant), neighbour group silent
#   m1      mutant: Q 1 group strapped for quadrant 0 (wrong quadrant id)      -> LOCKSTEP_FAIL (target not configured)
#   m2      mutant: Q 2 group, vmm bank pair 0/1 crossed                        -> LOCKSTEP_FAIL
#   m3      mutant: Q 3 group, vmm done steering one edge late (merge stage)    -> LOCKSTEP_FAIL
# usage: run_quant_vmm_q_lockstep.sh OUT [CASES]   (VERILATOR overrides the binary; default the daemon's 5.050)
set -euo pipefail
ulimit -c 0
out=$(realpath -m "$1"); mkdir -p "$out"
cases=${2:-"q0 q1 q2 q3 m1 m2 m3"}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv
 physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
 rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/lib/ot_rst_relay.sv
 rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_dec.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_split.sv rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_r2.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_r3.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_r4.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192/ot_sram_1r1w_128x64_m1_p192.v
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_lg_port_group.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_split_r2.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_record_calendar.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_host_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
 rtl/hbm_accel/generic/loader/ot_hgi_loader_cp.sv
 rtl/hbm_accel/index/quad_1017/ot_hbm_idx_vm_share2_static.sv
 rtl/hbm_accel/generic/vm/static/wq_merge/hfd_vms_wq2_merge.sv
 rtl/hbm_accel/generic/qw/static/quadrant/ot_hgi_qdq_q_program_leaf.sv
 rtl/hbm_accel/generic/qw/static/quadrant/ot_hgi_qdq_host_split_q.sv
 rtl/hbm_accel/generic/qw/static/quadrant/ot_hbm_quant_vmm_q.sv
 rtl/test/hbm_accel/generic/quant_q/tb_hbm_quant_vmm_q_lockstep.sv)
data=(tools/hgi_unit_tput/vectors/qdqvec results/hbm_static_quant_1015/compact_fixture.hex)
if [[ ${2:-} == --manifest ]]; then printf '%s\n' "${src[@]}" "${data[@]}"; exit; fi
"$V" --version | tee "$out/verilator.version"
sha256sum "${src[@]}" > "$out/sources.sha256"
for c in $cases; do
 q=0; mut=0
 case $c in q0) q=0;; q1) q=1;; q2) q=2;; q3) q=3;; m1) q=1; mut=1;; m2) q=2; mut=2;; m3) q=3; mut=3;; *) echo "unknown case $c"; exit 2;; esac
 G=(-GQ=$q -GMUT=$mut ${EXTRA_G:-})
 bld() { "$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style "${G[@]}" \
  --top-module tb_hbm_quant_vmm_q_lockstep -Mdir "$out/m$c.obj" -o sim "${src[@]}" > "$out/m$c.build" 2>&1; }
 bld || { sleep 5; bld; } || { tail -30 "$out/m$c.build"; exit 1; }
 set +e; "$out/m$c.obj/sim" +verilator+seed+${SEED:-7} +DIR=tools/hgi_unit_tput/vectors/qdqvec +PROGRAM=results/hbm_static_quant_1015/compact_fixture.hex > "$out/m$c.log" 2>&1; rc=$?; set -e
 echo "$rc" > "$out/m$c.rc"
 case $c in
  q*) grep -q '^PASS HBM_QUANT_VMM_Q_LOCKSTEP' "$out/m$c.log" || { tail -20 "$out/m$c.log"; exit 1; };;
  *) [[ $rc != 0 ]] || { echo "mutant $c survived"; exit 1; }; grep -q 'LOCKSTEP_FAIL' "$out/m$c.log" || { tail -5 "$out/m$c.log"; exit 1; };;
 esac
 echo "$c: $(grep -m1 -E 'PASS|LOCKSTEP_FAIL' "$out/m$c.log")"
 rm -rf "$out/m$c.obj"
done
echo "PASS QUANT_VMM_Q_LOCKSTEP_GATE cases $cases: every quadrant group == golden monolith (vm_rq +RQ_OFF+1, wq_m +WQ_OFF+2, done exact), neighbour silent; mutants killed" | tee "$out/gate"
