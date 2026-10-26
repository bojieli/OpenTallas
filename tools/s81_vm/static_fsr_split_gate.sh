#!/bin/bash
set -euo pipefail
S=${1:?flat source};O=${2:?outdir};mkdir -p "$O"
F=("$S/dsfd_vm_static_fsr_bank8.sv" "$S/dsfd_vm_static_fsr_quartets.sv" "$S/dsfd_vm_static_suhc_fsr.sv" "$S/tb_dsfd_vm_static_fsr_split.sv")
iverilog -g2012 -s tb_dsfd_vm_static_fsr_split -o "$O/base" "${F[@]}"
iverilog -g2012 -DOT_VM_FSR8_MUT_TAG -s tb_dsfd_vm_static_fsr_split -o "$O/mut" "${F[@]}"
for seed in 1 2;do vvp "$O/base" +mode=0 +seed=$seed > "$O/base_s$seed.log";grep -q 'FSR_SPLIT PASS mode0 ' "$O/base_s$seed.log";done
for mode in 1 2 3;do vvp "$O/base" +mode=$mode > "$O/fault_m$mode.log";grep -q "FSR_SPLIT PASS mode$mode " "$O/fault_m$mode.log";done
vvp "$O/mut" +mode=0 > "$O/mut_tag.log";grep -q 'FSR_SPLIT FAIL mode0 ' "$O/mut_tag.log"
echo 'STATIC_FSR_SPLIT_GATE PASS'
