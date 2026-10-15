#!/bin/bash
set -eu
S=$1;O=$2;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
build(){ "$V" --binary --timing -O1 -Wno-fatal -j 2 --top-module tb_dsfd_vm_static_scatter --Mdir "$O/obj_$1" -o tb ${2:-} "$S/dsfd_vm_static_scatter.sv" "$S/tb_dsfd_vm_static_scatter.sv" > "$O/build_$1.log" 2>&1; }
build base & p1=$!;build hash +define+OT_VM_SCATTER_MUT_HASH & p2=$!;build data +define+OT_VM_SCATTER_MUT_DATA & p3=$!
wait "$p1";wait "$p2";wait "$p3"
for c in base hash data;do "$O/obj_$c/tb" > "$O/run_$c.log" 2>&1;head -2 "$O/run_$c.log";done
grep -qx PASS "$O/run_base.log"
grep -qx FAIL "$O/run_hash.log"
grep -qx FAIL "$O/run_data.log"
echo STATIC_SCATTER_GATE_PASS
