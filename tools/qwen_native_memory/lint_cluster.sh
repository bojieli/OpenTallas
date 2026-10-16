#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?output directory};mkdir -p "$out"
cd "$root"
P=rtl/qwen_sys/vm_plane_20261013; S=rtl/qwen_sys/vm_die_split_20261012; N=rtl/qwen_sys/vm_nox_20261014
files=(
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
 "$N/ot_qfd_vm_region_nx.sv" "$P/ot_qfd_vm_region_leaf.sv" "$S/ot_qfd_vm_region_quarter.sv" "$S/ot_qfd_vm_answer_tiles.sv"
 "$S/ot_qfd_vm_xfifo8_t.sv" rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv
 rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv
 rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qwen_tree_delay.sv
 rtl/physical/ot_qwen_tree_delay_tiles.sv "$N/qfd_sp_vector_memory.sv" rtl/qwen_sys/dvm_20261014/ot_qfd_vm_q_export_fixed.sv
 rtl/qwen_sys/system_20261008/ot_qfd_crom.sv rtl/qwen_sys/redesign_qwen/ot_qfd_crom_lbuf.sv rtl/qwen_sys/native_memory_20261014/ot_qwen_native_memory_cluster.sv
)
sha256sum "${files[@]}" > "$out/source.sha256"
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --lint-only -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+OT_QFD_VM_NOX --top-module ot_qwen_native_memory_cluster "${files[@]}" > "$out/lint.log" 2>&1
# Q-VMWB 0030: '! grep' never trips set -e (negated pipelines are exempt), so this check PASSED with missing pins.
if grep -Eq 'PINMISSING|PINNOTFOUND|MODMISSING' "$out/lint.log"; then
  grep -E 'PINMISSING|PINNOTFOUND|MODMISSING' "$out/lint.log" | head -20; echo FAIL_native_cluster_unbound_pins; exit 1
fi
echo PASS_native_cluster_elaboration_real_SRAM_ROM_all_clock_ports
