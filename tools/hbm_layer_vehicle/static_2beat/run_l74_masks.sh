#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
o=$(realpath -m "${1:?output directory}");mkdir -p "$o"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for mode in good old badslot;do
 flags=();case "$mode" in old)flags=(-GOLD_MASK=1);;badslot)flags=(-GBAD_SLOT=1);;esac
 "$v" --binary --timing -j 1 -O1 -Wno-fatal --top-module tb_l74_masks "${flags[@]}" --Mdir "$o/obj_$mode"   rtl/hbm_accel/generic/transport/ot_hbm_static_2beat.sv tools/hbm_layer_vehicle/static_2beat/tb_l74_masks.sv > "$o/$mode.build.log" 2>&1
 set +e;"$o/obj_$mode/Vtb_l74_masks" > "$o/$mode.log" 2>&1;rc=$?;set -e
 if [ "$mode" = good ];then [ "$rc" = 0 ];else [ "$rc" != 0 ];fi
 grep -m1 L74_MASK "$o/$mode.log"
done
