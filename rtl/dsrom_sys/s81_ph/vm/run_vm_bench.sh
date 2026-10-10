#!/bin/bash
# CLAUDE S81-PH vm exact gate (lockstep vs a behavioural array VM, fixed latency): tb_ot_s81ph_vm_mem on the tiled
# 4 x dsfd_vm_bg chain (+define+TILED) or the v1 sub-macro.  Run from the repo root.
#   run_vm_bench.sh <out> <tag> "<verilator defines>" "<plusargs>"   exit 0 iff PASS (or PASS_OVF with +OVF)
set -u
O=$1; T=$2; D=${3:-}; A=${4:-}
mkdir -p $O
verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -j 8 --top-module tb_ot_s81ph_vm_mem $D \
  --Mdir $O/obj_$T rtl/dsrom_sys/s81_ph/test/tb_ot_s81ph_vm_mem.sv rtl/dsrom_sys/s81_ph/vm/ot_s81ph_vm_mem.sv \
  rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bg.sv \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v > $O/build_$T.log 2>&1 || { echo BUILD_FAIL; grep -m10 -i error $O/build_$T.log; exit 2; }
$O/obj_$T/Vtb_ot_s81ph_vm_mem $A > $O/run_$T.log 2>&1
grep -E "^RESULT|^OVF|^PASS|^FAIL" $O/run_$T.log | tail -3
grep -qE "^PASS$|PASS_OVF" $O/run_$T.log
