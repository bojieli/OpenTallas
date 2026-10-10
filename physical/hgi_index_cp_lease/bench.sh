#!/usr/bin/env bash
set -eu
mode=${1:-exact}
task_tmp=$(mktemp -d /tmp/hgi-index-cp-lease.XXXXXX)
trap 'rm -rf "$task_tmp"' EXIT
cp rtl/hbm_accel/control/ot_hgi_index_cp_lease.sv "$task_tmp/actor.sv"
if [[ "$mode" == mutant ]]; then
 sed -i "s/grant_frame==frame/1'b1/" "$task_tmp/actor.sv"
fi
iverilog -g2012 -s tb -o "$task_tmp/sim" "$task_tmp/actor.sv" rtl/hbm_accel/control/ot_hbm_native_index_control.sv physical/hgi_index_cp_lease/tb.sv
vvp "$task_tmp/sim"
