#!/bin/bash
# OWN-QDQ 10-18: lockstep of ot_hgi_qdq_host_split_r2 (d4g split r2: LG r2, strap ctl r3, one-tile decoder, NW target48
# programme leaf) against the monolith ot_hgi_qdq_host_static #(RL7,WC4,COMPACT1).
#   m0  positive, no relays            (rq +3, wq/done +9)
#   m4  positive, 12 relay stages/dir  (rq +15, wq/done +45; controller strapped RLI 35 / WCI 18)
#   m1  mutant: quant_NW0/1 write ports crossed (LGMUT=1)                       -> LOCKSTEP_FAIL
#   m2  mutant: 12 relay stages present, straps priced for 11 (one stage unpriced) -> LOCKSTEP_FAIL
# usage: run_qdq_host_split_r2_lockstep.sh OUT [CASES]  (CASES default "0 4 1 2"; VERILATOR overrides the binary)
set -euo pipefail
ulimit -c 0
out=$(realpath -m "$1"); mkdir -p "$out"
cases=${2:-"0 4 1 2"}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv
 physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
 rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv rtl/lib/ot_rst_relay.sv
 rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_dec.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_split.sv rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_r2.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_r3.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_lg_port_group.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_nw_program_leaf.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_split_r2.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_record_calendar.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_host_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
 rtl/hbm_accel/generic/loader/ot_hgi_loader_cp.sv
 rtl/test/hbm_accel/generic/tb_hgi_qdq_host_split_r2_lockstep.sv)
data=(tools/hgi_unit_tput/vectors/qdqvec results/hbm_static_quant_1015/compact_fixture.hex)
if [[ ${2:-} == --manifest ]]; then printf '%s\n' "${src[@]}" "${data[@]}"; exit; fi
"$V" --version | tee "$out/verilator.version"
for c in $cases; do
 case $c in 0) mut=0; xrs=0;; 4) mut=0; xrs=12;; 1) mut=1; xrs=0;; 2) mut=2; xrs=12;; *) echo "unknown case $c"; exit 2;; esac
 "$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=$mut -GXRS=$xrs \
  --top-module tb_hgi_qdq_host_split_r2_lockstep -Mdir "$out/m$c.obj" -o sim "${src[@]}" > "$out/m$c.build" 2>&1 \
  || { sleep 5; "$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -GMUT=$mut -GXRS=$xrs \
  --top-module tb_hgi_qdq_host_split_r2_lockstep -Mdir "$out/m$c.obj" -o sim "${src[@]}" > "$out/m$c.build" 2>&1; } \
  || { tail -30 "$out/m$c.build"; exit 1; }
 set +e; "$out/m$c.obj/sim" +DIR=tools/hgi_unit_tput/vectors/qdqvec +PROGRAM=results/hbm_static_quant_1015/compact_fixture.hex > "$out/m$c.log" 2>&1; rc=$?; set -e
 echo "$rc" > "$out/m$c.rc"
 if [[ $mut == 0 ]]; then grep -q '^PASS HGI_QDQ_HOST_SPLIT_R2_LOCKSTEP' "$out/m$c.log" || { tail -20 "$out/m$c.log"; exit 1; }
 else [[ $rc != 0 ]] || { echo "mutant $c survived"; exit 1; }; grep -q 'LOCKSTEP_FAIL' "$out/m$c.log" || { tail -5 "$out/m$c.log"; exit 1; }
 fi
 head -3 "$out/m$c.log"
 rm -rf "$out/m$c.obj"
done
echo "PASS QDQ_HOST_SPLIT_R2_LOCKSTEP_GATE cases $cases: split r2 == monolith (rq +3+XR, wq/done +9+3XR) golden writes; mutants killed (LOCKSTEP_FAIL)" | tee "$out/gate"
