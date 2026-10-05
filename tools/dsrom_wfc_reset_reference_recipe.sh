#!/usr/bin/env bash
# Compile only the additive bench successor, not the pinned donor bench.
# This prepares a runnable owner recipe; it does not run anything by itself.
# Run remotely in a pinned clean checkout under the existing fleet admission:
#   /srv/opentallas-scratch/admit.sh 12 -- bash tools/dsrom_wfc_reset_reference_recipe.sh NEW_OUT [existing -G arguments]
# SOURCE0 keeps LOCKSTEP=1. SOURCE1 must retain its existing LOCKSTEP=0 setting.
# No seed/geometry/checker change is made here; caller supplies its retained -G set.
set -euo pipefail
output=${1:?Usage: dsrom_wfc_reset_reference_recipe.sh NEW_OUT [retained -G arguments]}
shift
if [[ -e "$output" ]]; then
    echo "Refusing to overwrite existing output: $output" >&2
    exit 2
fi
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p -- "$output"
output=$(cd -- "$output" && pwd)
verilator --binary --timing -Wno-fatal -j 4 \
    --top-module tb_wf_ctrl_equiv -DWF_DUT=ot_rom_pkg_ctrl_wfc \
    --Mdir "$output/obj" "$@" \
    "$repo/rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv" \
    "$repo/rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv" \
    "$repo/rtl/test/dsrom_wavefront/tb_wf_ctrl_equiv_reset_admission.sv" \
    > "$output/build.log" 2>&1
"$output/obj/Vtb_wf_ctrl_equiv" > "$output/run.log" 2>&1
cat "$output/run.log"
if ! grep -q 'EQUIV PASS' "$output/run.log" || grep -q 'EQUIV FAIL' "$output/run.log"; then
    exit 1
fi
