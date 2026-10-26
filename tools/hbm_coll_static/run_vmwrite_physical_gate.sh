#!/usr/bin/env bash
set -euo pipefail
mutation=$1
out=$2
mkdir -p "$out"
out=$(realpath "$out")
base=rtl/hbm_accel/generic/collective/p2p
verilator --binary --timing -Wno-fatal --top-module tb_hgi_coll_static_vmwrite -j 2 --Mdir "$out/obj" -GMUT="$mutation" "$base/ot_hgi_coll_static_vmwrite.sv" "$base/tb_hgi_coll_static_vmwrite.sv" > "$out/build.log" 2>&1
"$out/obj/Vtb_hgi_coll_static_vmwrite"
