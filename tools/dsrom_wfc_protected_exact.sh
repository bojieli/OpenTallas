#!/usr/bin/env bash
# New actual-provider-connected mechanism only; no passing source replay.
set -euo pipefail
output=${1:?new immutable output root}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test ! -e "$output";mkdir -p "$output"
compiler=${OT_WFC_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$compiler" --version >"$output/tool.txt"
sources=(
 "$repo/rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv"
 "$repo/rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv"
 "$repo/rtl/dsrom_sys/protected_vm/ot_dsrom_vm_codec.sv"
 "$repo/rtl/dsrom_sys/protected_vm/ot_dsrom_vm_ratio_fifo.sv"
 "$repo/rtl/dsrom_sys/protected_vm/ot_dsrom_vm_backend.sv"
 "$repo/rtl/dsrom_sys/protected_vm/ot_dsrom_protected_vm.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_vm_caller_adapter.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_protected_stage.sv"
 "$repo/rtl/rom/wavefront/context/protected_20261006/ot_dsrom_wfc_enclosing_vm_stage.sv"
 "$repo/rtl/rom/wavefront/context/protected_20261006/ot_dsrom_wfc_parent_enclosed_vm.sv"
 "$repo/rtl/rom/wavefront/context/protected_20261006/ot_rom_pkg_ctrl_wfc_enclosed_vm.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_vm_port.sv"
 "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_router_cut.sv"
 "$repo/rtl/rom/ot_rom_fabric_router.sv"
 "$repo/rtl/dsrom_sys/c8/ot_dsrom_c8_stage_context.sv"
 "$repo/rtl/dsrom_sys/wfc_producers/ot_dsrom_wfc_cfg_prompt.sv"
 "$repo/rtl/dsrom_sys/wfc_producers/ot_dsrom_wfc_whole_stage.sv"
 "$repo/rtl/dft/ot_rom_secded_dec.sv"
 "$repo/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
 "$repo/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v"
 "$repo/rtl/test/dsrom_wavefront/tb_wfc_protected_stage.sv"
)
"$compiler" --binary --timing -Wno-fatal -j 4 --top-module tb_wfc_protected_stage \
 --Mdir "$output/obj" "${sources[@]}" >"$output/build.log" 2>&1
(cd "$repo" && "$output/obj/Vtb_wfc_protected_stage") >"$output/run.log" 2>&1
grep -q 'PROTECTED_JOIN_NOMINAL PASS' "$output/run.log"
grep -q 'PROTECTED_JOIN_NEGATIVE PASS' "$output/run.log"
grep -q 'PROTECTED_JOIN_MECHANISM PASS' "$output/run.log"
printf 'PASS_ACTUAL_PROTECTED_PROVIDER_JOIN_NOT_PHYSICAL_QUALIFICATION\n' >"$output/verdict"
