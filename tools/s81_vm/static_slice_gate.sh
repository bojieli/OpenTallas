#!/bin/bash
set -eu
S=$1;O=$2;TOP=${3:-tb_dsfd_vm_static_slice128};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
build(){ "$V" --binary --timing -O1 -Wno-fatal -j 2 --top-module "$TOP" --Mdir "$O/obj_$1" -o tb ${2:-} "$S/dsfd_vm_static_rscatter.sv" "$S/dsfd_vm_static_scatter.sv" "$S/dsfd_vm_static_bank128.sv" "$S/dsfd_vm_static_slice128.sv" "$S/ot_sram_1r1w_512x128_m4_r2c2.v" "$S/dsfd_vm_static_return.sv" "$S/$TOP.sv" > "$O/build_$1.log" 2>&1; }
build base & p1=$!;build mutant +define+OT_VM_BANK_MUT_MASK & p2=$!;p3=''
if [ "$TOP" = tb_dsfd_vm_static_group128 ];then build early +define+OT_VM_GROUP_MUT_EARLY_RELEASE & p3=$!;fi
wait "$p1";wait "$p2";if [ -n "$p3" ];then wait "$p3";fi
for c in base mutant;do "$O/obj_$c/tb" > "$O/run_$c.log" 2>&1;head -2 "$O/run_$c.log";done
grep -qx PASS "$O/run_base.log";grep -qx FAIL "$O/run_mutant.log"
if [ -n "$p3" ];then "$O/obj_early/tb" > "$O/run_early.log" 2>&1;head -2 "$O/run_early.log";grep -qx FAIL "$O/run_early.log";fi
echo STATIC_SLICE_GATE_PASS
