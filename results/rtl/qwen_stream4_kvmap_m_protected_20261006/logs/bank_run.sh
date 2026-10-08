#!/bin/bash
cd /srv/opentallas-scratch/claude/tk-qwen-kvm-bank
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
b(){ n=$1; shift; $V --binary --timing --threads 1 -O3 -j 8 --top-module tb_qwen_p0_parallel_bank -Wno-fatal -Wno-TIMESCALEMOD --Mdir obj_$n "$@" -y rtl/hdc/kv -y rtl/hdc/v41x -y rtl/hdc -y rtl/lib -y rtl/experimental/w2_nc6_protection_20261003 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/hdc/kv/ot_qwen_s4_parallel_protected_pc.sv rtl/experimental/qwen_rom_combined_p0_20261005/ot_qwen_p0_parallel_bank.sv rtl/experimental/qwen_rom_combined_p0_20261005/tb_qwen_p0_parallel_bank.sv > b_$n.log 2>&1 || { echo "$n build FAIL" >> summary.txt; return; }
  obj_$n/Vtb_qwen_p0_parallel_bank +GOLD=gold.hex > r_$n.log 2>&1; echo "$n rc=$?" >> summary.txt; }
b m0 -GKV_MAP=0 & b m1 -GKV_MAP=1 & b neg -GKV_MAP=1 -GKV_MAP_DUT=0 & wait; echo DONE > DONE
