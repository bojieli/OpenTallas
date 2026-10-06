#!/usr/bin/env bash
# Minimum new enclosing mechanism only; retained full866 controller gate reused.
set -euo pipefail
output=${1:?new immutable output root}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test ! -e "$output";mkdir -p "$output"
verilator --binary --timing -Wno-fatal -j 4 --top-module tb_wfc_enclosing_stage \
 --Mdir "$output/obj" \
 "$repo/rtl/test/dsrom_wavefront/tb_wfc_enclosing_stage.sv" \
 "$repo/rtl/rom/wavefront/context/enclosing_20261005/ot_rom_pkg_ctrl_wfc_enclosed.sv" \
 "$repo/rtl/rom/wavefront/context/enclosing_20261005/ot_dsrom_wfc_parent_enclosed.sv" \
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_enclosing_stage.sv" \
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_vm_port.sv" \
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_router_cut.sv" \
 "$repo/rtl/rom/ot_rom_fabric_router.sv" \
 "$repo/rtl/dsrom_sys/c8/ot_dsrom_c8_stage_context.sv" >"$output/build.log" 2>&1
(cd "$output" && ./obj/Vtb_wfc_enclosing_stage) >"$output/run.log" 2>&1
grep -q 'ENCLOSING_MINIMUM_MECHANISM PASS' "$output/run.log"
printf 'PASS_MINIMUM_ENCLOSING_MECHANISM_CANONICAL_PRODUCER_BINDING_PENDING\n' >"$output/verdict"
