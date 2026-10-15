#!/bin/bash
set -u
cd /srv/opentallas-scratch/claude/qvm-bank-native-1015
for mut in 0 1 2;do
 out=/srv/opentallas-scratch/claude/qvm-bank-native-1015/m$mut
 mkdir -p "$out"
 $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -Wno-fatal --top-module tb_qvm_bank_native -GMUT=$mut -j 2 --Mdir "$out" rtl/qwen_sys/vm_native_physical_20261015/tb_qvm_bank_native.sv rtl/qwen_sys/vm_native_physical_20261015/qvm_bank_native.sv rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_region_leaf.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v > "$out/build.log" 2>&1 || exit 2
 "$out/Vtb_qvm_bank_native" > "$out/run.log" 2>&1
 rc=$?;cat "$out/run.log"
 if [ "$mut" = 0 ] && [ "$rc" != 0 ];then exit 3;fi
 if [ "$mut" = 1 ] && [ "$rc" = 0 ];then exit 4;fi
done
