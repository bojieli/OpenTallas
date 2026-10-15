#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../.."
out=${1:?outdir}; mode=${2:-base}
mkdir -p "$out"
defs=()
case "$mode" in
base) ;;
stride) defs+=(-DOT_VM_LANDING_LANE_MUT_STRIDE);;
rowskew) defs+=(-DOT_VM_LANDING_LANE_MUT_ROWSKEW);;
*) exit 2;;
esac
iverilog -g2012 "${defs[@]}" -s tb -o "$out/tb" tools/s81_vm/landing_lane_bench.sv \
 rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_landing.sv rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_landing_lane.sv
vvp "$out/tb" | tee "$out/run.log"
