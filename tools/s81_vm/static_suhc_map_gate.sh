#!/bin/bash
set -eu
S=$1;O=$2;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
build(){ "$V" --binary --timing -O1 -Wno-fatal -j 2 --top-module tb_dsfd_vm_static_suhc_map --Mdir "$O/obj_$1" -o tb ${2:-} "$S/dsfd_vm_static_suhc_fsr.sv" "$S/dsfd_vm_static_suhc_return_map.sv" "$S/tb_dsfd_vm_static_suhc_map.sv" > "$O/build_$1.log" 2>&1; }
build base & p1=$!;build tag +define+OT_VM_SUHC_FSR_MUT_TAG & p2=$!;build select +define+OT_VM_SUHC_MAP_MUT_SELECT & p3=$!;wait "$p1";wait "$p2";wait "$p3"
for l in L0 L2 L14 L20;do
 for c in base tag select;do "$O/obj_$c/tb" +TRACE="$S/read_map_inputs/$l.txt" > "$O/run_${l}_${c}.log" 2>&1;head -2 "$O/run_${l}_${c}.log";done
 grep -qx PASS "$O/run_${l}_base.log";grep -qx FAIL "$O/run_${l}_tag.log";grep -qx FAIL "$O/run_${l}_select.log"
done
echo STATIC_SUHC_MAP_GATE_PASS
