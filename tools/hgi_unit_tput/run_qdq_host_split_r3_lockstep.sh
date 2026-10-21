#!/bin/bash
# HBM-QDQ8 10-20: lockstep of ot_hgi_qdq_host_split_r3 (split r2 + deep strap ctl_r4, SRAM command ring) against the
# monolith ot_hgi_qdq_host_static #(RL=L,WC4,COMPACT1), both on a fixed-latency VM model of L edges at the pins.
#   a  positive, L 7,  no relays        (RLI 11: the r2 m0 point)
#   b  positive, L 54, no relays        (RLI 58: GEN2e4 r11 functional_bind need for hb_quant_NW)
#   c  positive, L 54, 12 relays/dir    (RLI 82 / WCI 18)
#   m2 mutant: L 54, 12 relays present, straps priced for 11              -> LOCKSTEP_FAIL
#   m3 mutant: L 54, ctl_r4 ring read one entry late (MUT 3)              -> LOCKSTEP_FAIL
#   d  defect witness: split r2 (ctl_r3) at L 54 -> elaboration fatal 'RLI 1..46' (ctl_r3 cannot take the die latency)
# usage: run_qdq_host_split_r3_lockstep.sh OUT [CASES]  (CASES default "a b c m2 m3 d"; VERILATOR overrides the binary)
set -euo pipefail
ulimit -c 0
out=$(realpath -m "$1"); mkdir -p "$out"
cases=${2:-"a b c m2 m3 d"}
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
 physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192/ot_sram_1r1w_128x64_m1_p192.v
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_lg_port_group.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_static.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_nw_program_leaf.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_split_r2.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_split_r3.sv
 rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_record_calendar.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_host_static.sv
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
 rtl/hbm_accel/generic/loader/ot_hgi_loader_cp.sv
 rtl/test/hbm_accel/generic/tb_hgi_qdq_host_split_r2_lockstep.sv)
data=(tools/hgi_unit_tput/vectors/qdqvec results/hbm_static_quant_1015/compact_fixture.hex)
if [[ ${2:-} == --manifest ]]; then printf '%s\n' "${src[@]}" "${data[@]}"; exit; fi
"$V" --version | tee "$out/verilator.version"
for c in $cases; do
 rev=3; l=54; xrs=0; mut=0
 case $c in a) l=7;; b) ;; c) xrs=12;; m2) xrs=12; mut=2;; m3) mut=3;; d) rev=2;; *) echo "unknown case $c"; exit 2;; esac
 G=(-GMUT=$mut -GXRS=$xrs -GL=$l -GREV=$rev)
 bld() { "$V" --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style "${G[@]}" \
  --top-module tb_hgi_qdq_host_split_r2_lockstep -Mdir "$out/m$c.obj" -o sim "${src[@]}" > "$out/m$c.build" 2>&1; }
 bld || { sleep 5; bld; } || { tail -30 "$out/m$c.build"; exit 1; }
 set +e; "$out/m$c.obj/sim" +DIR=tools/hgi_unit_tput/vectors/qdqvec +PROGRAM=results/hbm_static_quant_1015/compact_fixture.hex > "$out/m$c.log" 2>&1; rc=$?; set -e
 echo "$rc" > "$out/m$c.rc"
 case $c in
  a|b|c) grep -q '^PASS HGI_QDQ_HOST_SPLIT_R2_LOCKSTEP' "$out/m$c.log" || { tail -20 "$out/m$c.log"; exit 1; };;
  d) [[ $rc != 0 ]] && grep -q 'RLI 1..46' "$out/m$c.log" || { echo "defect witness d did not fail as expected"; tail -5 "$out/m$c.log"; exit 1; };;
  *) [[ $rc != 0 ]] || { echo "mutant $c survived"; exit 1; }; grep -q 'LOCKSTEP_FAIL' "$out/m$c.log" || { tail -5 "$out/m$c.log"; exit 1; };;
 esac
 head -3 "$out/m$c.log"
 rm -rf "$out/m$c.obj"
done
echo "PASS QDQ_HOST_SPLIT_R3_LOCKSTEP_GATE cases $cases: split r3 (ctl_r4 ring) == monolith at L 7 / 54 (rq +3+XR, wq/done +9+3XR); mutants killed; ctl_r3 refuses L 54" | tee "$out/gate"
