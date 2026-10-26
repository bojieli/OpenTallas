#!/bin/bash
set -euo pipefail
root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
cd "$root"
out=${1:?fresh output directory}
test ! -e "$out" || { echo REFUSE_EXISTING_OUTPUT; exit 2; }
mkdir -p "$out"
git rev-parse HEAD > "$out/source_commit.txt"
src=(rtl/hbm_accel/generic/collective/p2p/tb_hbm_vmface.sv
 rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_ctl_v5.sv
 rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_slice_v7.sv
 rtl/hdc/ot_hdc_prefix.sv tools/hbm_b2/vmface/ctl_gold.sv)
sha256sum "${src[@]}" > "$out/sources.sha256"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_vmface --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1
"$out/obj/Vtb_hbm_vmface" > "$out/sim.log" 2>&1
grep -q '^VMFACE_MITER_PASS ' "$out/sim.log"
cat "$out/sim.log"
echo VMFACE_GATE_PASS
