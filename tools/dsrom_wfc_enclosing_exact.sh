#!/usr/bin/env bash
# Minimum new enclosing mechanics only; full866 controller exact is retained.
set -euo pipefail
output=${1:?new immutable output root}
top=${2:-tb_wfc_enclosing_stage}
case "$top" in
 tb_wfc_enclosing_stage) pass=ENCLOSING_MINIMUM_MECHANISM;;
 tb_wfc_enclosing_wrong_owner) pass=ENCLOSING_WRONG_OWNER_ALL;;
 *) exit 2;;
esac
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test ! -e "$output";mkdir -p "$output"
sources=(
 "$repo/rtl/rom/wavefront/context/enclosing_20261005/ot_rom_pkg_ctrl_wfc_enclosed.sv"
 "$repo/rtl/rom/wavefront/context/enclosing_20261005/ot_dsrom_wfc_parent_enclosed.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_enclosing_stage.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_vm_port.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_router_cut.sv"
 "$repo/rtl/rom/ot_rom_fabric_router.sv"
 "$repo/rtl/dsrom_sys/c8/ot_dsrom_c8_stage_context.sv"
)
verilator --binary --timing -Wno-fatal -j 4 --top-module "$top" \
 --Mdir "$output/obj" "$repo/rtl/test/dsrom_wavefront/tb_wfc_enclosing_stage.sv" \
 "${sources[@]}" >"$output/build.log" 2>&1
(cd "$output" && ./obj/V"$top") >"$output/run.log" 2>&1
grep -q "$pass PASS" "$output/run.log"
if [[ "$top" = tb_wfc_enclosing_wrong_owner ]]; then
 # Necessary new SOURCE1 enclosing wiring elaboration, no numerical replay.
 verilator --lint-only --timing -Wno-fatal --top-module ot_dsrom_wfc_enclosing_stage \
  -GENABLE=1 -GSOURCE=1 -GSTRUCTURAL=1 --Mdir "$output/source1_elab" \
  "${sources[@]}" >"$output/source1_elab.log" 2>&1
 printf '0\n' >"$output/source1_elab.exit"
fi
printf 'PASS_MINIMUM_ENCLOSING_MECHANISM_CANONICAL_PRODUCER_BINDING_PENDING\n' >"$output/verdict"
