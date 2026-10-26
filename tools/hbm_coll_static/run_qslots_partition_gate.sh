#!/usr/bin/env bash
set -euo pipefail
npt=$1
mutation=$2
out=$3
mkdir -p "$out"
out=$(realpath "$out")
base=rtl/hbm_accel/generic/collective/p2p
mutargs=()
if [[ $mutation == select ]];then mutargs=(-GMUT_SELECT=1);fi
if [[ $mutation == latency ]];then mutargs=(-GMUT_PIN_LATENCY=1);fi
verilator --binary --timing -Wno-fatal --top-module tb_qslots_partitioned_v1 -j 2 --Mdir "$out/obj" -GNPT="$npt" "${mutargs[@]}" "$base/ot_hgi_coll_qslots.sv" "$base/ot_hgi_coll_qslots_partitioned_v1.sv" tools/hbm_coll_static/tb_qslots_partitioned_v1.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_qslots_partitioned_v1"
