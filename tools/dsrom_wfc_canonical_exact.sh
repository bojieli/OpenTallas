#!/usr/bin/env bash
# Sole new active hookup mechanism; prior full866/component proofs are reused.
set -euo pipefail
output=${1:?new immutable output root}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test ! -e "$output";mkdir -p "$output"
compiler=${OT_WFC_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$compiler" --version >"$output/tool.txt"
sources=(
 "$repo/rtl/test/dsrom_wavefront/tb_wfc_canonical_stage.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_canonical_stage.sv"
 "$repo/rtl/dsrom_sys/wfc_producers/ot_dsrom_wfc_cfg_prompt.sv"
 "$repo/rtl/dsrom_sys/wfc_producers/ot_dsrom_wfc_whole_stage.sv"
 "$repo/rtl/dft/ot_rom_secded_dec.sv"
 "$repo/rtl/rom/wavefront/context/enclosing_20261005/ot_rom_pkg_ctrl_wfc_enclosed.sv"
 "$repo/rtl/rom/wavefront/context/enclosing_20261005/ot_dsrom_wfc_parent_enclosed.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_enclosing_stage.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_vm_port.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_router_cut.sv"
 "$repo/rtl/rom/ot_rom_fabric_router.sv"
 "$repo/rtl/dsrom_sys/c8/ot_dsrom_c8_stage_context.sv"
 "$repo/physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
 "$repo/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v"
)
"$compiler" --binary --timing -Wno-fatal -j 4 --top-module tb_wfc_canonical_stage \
 --Mdir "$output/obj" "${sources[@]}" >"$output/build.log" 2>&1
# ROM book paths are pinned repository-relative; outputs live on compute host.
(cd "$repo" && "$output/obj/Vtb_wfc_canonical_stage") >"$output/run.log" 2>&1
grep -q 'CANONICAL_ACTIVE_NOMINAL PASS' "$output/run.log"
grep -q 'CANONICAL_ACTIVE_NEGATIVE PASS' "$output/run.log"
grep -q 'CANONICAL_ACTIVE_MECHANISM PASS' "$output/run.log"
printf 'PASS_CANONICAL_ACTIVE_MECHANISM_NOT_PHYSICAL_QUALIFICATION\n' >"$output/verdict"
