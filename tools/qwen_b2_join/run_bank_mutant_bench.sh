#!/bin/bash
set -eu
out=$1
P=rtl/qwen_sys/vm_plane_20261013; S=rtl/qwen_sys/vm_die_split_20261012; N=rtl/qwen_sys/vm_nox_20261014
F="physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v $N/qfd_vm_attention_commit_fence.sv $N/ot_qfd_vm_region_nx.sv $P/ot_qfd_vm_region_leaf.sv $S/ot_qfd_vm_region_quarter.sv $S/ot_qfd_vm_answer_tiles.sv
 $S/ot_qfd_vm_xfifo8_t.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv $P/ot_qfd_vm_xplane.sv $P/ot_qfd_vm_xtree.sv
 rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv
 rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qwen_tree_delay.sv
 rtl/physical/ot_qwen_tree_delay_tiles.sv rtl/qwen_split/qfd_su_vm_pack.sv $N/qfd_sp_vector_memory_b2.sv $N/qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3.sv rtl/qwen_sys/vm_native_physical_20261015/qvm_return_plane_pin_native.sv rtl/qwen_split/qfd_res_train_half_b2.sv rtl/qwen_split/qfd_res_train_half_b2_wrappers.sv tools/qwen_b2_join/tb_b2_train_e3.sv rtl/qwen_sys/dvm_20261014/ot_qfd_vm_q_export_fixed.sv rtl/qwen_sys/vm_native_physical_20261015/qvm_bank_banked_native.sv rtl/qwen_sys/vm_native_physical_20261015/qvm_su_bank_native.sv"
mkdir -p "$out"
sha256sum $F > "$out/source.sha256"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH +define+OT_QFD_B2_LATE_CAPTURE +define+OT_QFD_VM_NOX +define+OT_QFD_VM_PARTITIONED_CLOCKS --top-module tb_b2_train_e3 --Mdir "$out/obj" $F > "$out/build.log" 2>&1
if "$out/obj/Vtb_b2_train_e3" > "$out/mutant.log" 2>&1;then echo "actual late-capture RTL mutant survived";exit 1;fi
grep -q 'exact RB calendar/data mismatch' "$out/mutant.log"
echo "PASS actual b2 bank late-capture RTL mutant rejected"
