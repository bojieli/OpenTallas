#!/usr/bin/env bash
set -euo pipefail
mutation=$1
out=$2
mkdir -p "$out"
out=$(realpath "$out")
verilator --binary --timing -Wno-fatal --top-module tb_static_state_lane -j 2 --Mdir "$out/obj" -GMUT_READ_SOURCE="$mutation" rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_pring_static.sv tools/hbm_coll_static/tb_static_state_lane.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_static_state_lane"
