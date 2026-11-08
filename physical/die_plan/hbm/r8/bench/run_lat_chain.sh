#!/usr/bin/env bash
# DIE-HBM-92-LAT: build + run tb_hbm_lat_chain.sv on the real RTL of SRC (a kit source tree).
#   run_lat_chain.sh NAME MODE [iverilog -P overrides...]  -> OUT/NAME.log, prints the LATCHAIN line
set -u
SRC=${SRC:-/srv/opentallas-scratch2/claude/hbm-bind-6/tip2}   # the p37su5 manifest base
OUT=${OUT:-/srv/opentallas-scratch2/claude/die-hbm-92-lat/bench/out}
H=$(cd "$(dirname "$0")" && pwd)
n=$1; m=$2; shift 2
mkdir -p $OUT
# as-built source resolution of the HBM manifests (asbuilt_p37*: `prefer` = the r18h5 bundle copy, else rtl/)
pick() { if [ -f $SRC/physical/die_plan/hbm/bind/r18h5_bundle/$1 ]; then echo $SRC/physical/die_plan/hbm/bind/r18h5_bundle/$1; else echo $SRC/$1; fi; }
G=rtl/hbm_accel/generic
F="$H/tb_hbm_lat_chain.sv"
for r in $G/peers/ot_hgi_sfu_vm_static_bridge.sv $G/peers/ot_hgi_sfu_lg_pair_tap_leaf.sv $G/peers/ot_hgi_sfu_lg_pair_leaf.sv \
  $G/vm/static/ot_hbm_vm_lg_pair_tap.sv $G/vm/static/ot_hbm_vm_lg_static_bank.sv $G/vm/static/ot_hbm_vm_lg_static_bank_term.sv \
  $G/peers/static_hc/ot_hbm_hc_q_static.sv $G/peers/static_hc/ot_hgi_hc_residual_vm_static.sv \
  $G/peers/static_hc/ot_hgi_hc_result_vm_static.sv $G/peers/static_hc/ot_hgi_hc_gathered_mix_reader_static.sv \
  $G/vm/static/ot_vms_calendar_static.sv $G/vm/static/ot_static_program_target.sv rtl/hdc/ot_hdc_delay.sv \
  rtl/test/full_sm_service/sram_models.sv rtl/lib/ot_rst_relay.sv $G/peers/static_hc/ot_hbm_hc_xw_rx_static.sv; do
  F="$F $(pick $r)"; done
[ -n "${LIST:-}" ] && { echo $F | tr ' ' '\n'; exit 0; }
if iverilog -g2012 -o $OUT/$n.vvp -Ptb_hbm_lat_chain.MODE=$m "$@" $F > $OUT/$n.build.log 2>&1; then
  vvp -n $OUT/$n.vvp > $OUT/$n.log 2>&1; r=$(grep LATCHAIN $OUT/$n.log); echo "$n $r"; rm -f $OUT/$n.vvp
else echo "$n BUILD FAILED"; tail -15 $OUT/$n.build.log; fi
