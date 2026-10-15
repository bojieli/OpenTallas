#!/bin/bash
set -eu
out=$1; shift
P=rtl/qwen_sys/vm_plane_20261013; S=rtl/qwen_sys/vm_die_split_20261012; N=rtl/qwen_sys/vm_nox_20261014
F="physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v $N/ot_qfd_vm_region_nx.sv $P/ot_qfd_vm_region_leaf.sv $S/ot_qfd_vm_region_quarter.sv $S/ot_qfd_vm_answer_tiles.sv
 $S/ot_qfd_vm_xfifo8_t.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv $P/ot_qfd_vm_xplane.sv $P/ot_qfd_vm_xtree.sv
 rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv
 rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qwen_tree_delay.sv
 rtl/physical/ot_qwen_tree_delay_tiles.sv rtl/qwen_split/qfd_su_vm_pack.sv $N/qfd_sp_vector_memory.sv $N/tb_qfd_vm_su_replay.sv rtl/qwen_split/qfd_su_static_copy.sv rtl/qwen_sys/dvm_20261014/ot_qfd_vm_q_export_fixed.sv"
mkdir -p "$out"
$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH +define+OT_QFD_VM_NOX --top-module tb_qfd_vm_su_replay --Mdir "$out/obj" "$@" $F > "$out/build.log" 2>&1
"$out/obj/Vtb_qfd_vm_su_replay" > "$out/run.log" 2>&1
cat "$out/run.log"
grep -q '^PASS' "$out/run.log"
