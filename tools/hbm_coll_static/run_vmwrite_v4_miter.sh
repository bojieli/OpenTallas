#!/usr/bin/env bash
# Full-shape miter of the two-stage writer v4 against the frozen pin-capture v2 reference (kq/launch_done +1 edge,
# fault same edge). usage: run_vmwrite_v4_miter.sh OUT
set -euo pipefail
out=$1; mkdir -p "$out"; out=$(realpath "$out")
base=rtl/hbm_accel/generic/collective/p2p
verilator --binary --timing -Wno-fatal --top-module tb_vmwrite_v4_equiv -j 2 --Mdir "$out/obj" "$base/ot_hgi_coll_static_vmwrite.sv" tools/hbm_coll_static/vmwrite_v2_reference.sv tools/hbm_coll_static/tb_vmwrite_v4_equiv.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_vmwrite_v4_equiv"
