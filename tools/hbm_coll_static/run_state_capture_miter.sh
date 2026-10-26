#!/usr/bin/env bash
set -euo pipefail
mut=$1
out=$(realpath -m "$2")
mkdir -p "$out"
verilator --binary --timing -Wno-fatal --top-module tb_state_capture_miter -j 2 --Mdir "$out/obj" -GMUT="$mut" rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_pring_static.sv rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_pring_static_state_capture.sv tools/hbm_coll_static/tb_state_capture_miter.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_state_capture_miter"
