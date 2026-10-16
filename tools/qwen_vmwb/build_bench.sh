#!/bin/bash
# Q-VMWB: build the write-back bench (tb_vmwb) against the real VM file list of tools/qwen_tp8/vm_die_static_bench.sh.
# usage: build_bench.sh OUTDIR [verilator -G overrides...]
set -eu
R=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); cd "$R"
out=$1; shift
P=rtl/qwen_sys/vm_plane_20261013; S=rtl/qwen_sys/vm_die_split_20261012; N=rtl/qwen_sys/vm_nox_20261014
F="physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v $N/qfd_vm_attention_commit_fence.sv $N/ot_qfd_vm_region_nx.sv $P/ot_qfd_vm_region_leaf.sv $S/ot_qfd_vm_region_quarter.sv $S/ot_qfd_vm_answer_tiles.sv
 $S/ot_qfd_vm_xfifo8_t.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv $P/ot_qfd_vm_xplane.sv $P/ot_qfd_vm_xtree.sv
 rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv
 rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qwen_tree_delay.sv
 rtl/physical/ot_qwen_tree_delay_tiles.sv rtl/qwen_split/qfd_su_vm_pack.sv $N/qfd_sp_vector_memory.sv rtl/qwen_sys/dvm_20261014/ot_qfd_vm_q_export_fixed.sv rtl/qwen_sys/vm_native_physical_20261015/qvm_bank_banked_native.sv rtl/qwen_sys/vm_native_physical_20261015/qvm_su_bank_native.sv
 tools/qwen_producer_train/component_sources.sv rtl/qwen_split/qfd_res_train_static.sv rtl/qwen_split/qfd_res_train_par.sv rtl/qwen_split/qfd_res_train_issue.sv
 results/arch/qwen_split_compute_1014/vmwb_1015/tb_vmwb.sv"
mkdir -p "$out"
sha256sum $F > "$out/executed_source.sha256"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -j ${J:-16} -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN +define+OT_QFD_VM_NOX --top-module tb_vmwb --Mdir "$out/obj" "$@" $F > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; exit 1; }
sha256sum "$out/obj/Vtb_vmwb" > "$out/executable.sha256"
