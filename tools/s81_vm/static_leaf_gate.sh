#!/bin/bash
set -eu
S=$1;O=$2;LEAF=$3;TOP=$4;MUT=$5;mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
MEM=$S/ot_sram_1r1w_512x128_m4_r2c2.v
EXTRA=();if [ "$LEAF" = dsfd_vm_static_bank128 ];then EXTRA=("$MEM");fi
build(){ "$V" --binary --timing -O1 -Wno-fatal -j 2 --top-module "$TOP" --Mdir "$O/obj_$1" -o tb ${2:-} "$S/$LEAF.sv" "$S/$TOP.sv" "${EXTRA[@]}" > "$O/build_$1.log" 2>&1; }
build base & p1=$!;build mutant "+define+$MUT" & p2=$!;wait "$p1";wait "$p2"
for c in base mutant;do "$O/obj_$c/tb" > "$O/run_$c.log" 2>&1;head -2 "$O/run_$c.log";done
grep -qx PASS "$O/run_base.log";grep -qx FAIL "$O/run_mutant.log"
echo STATIC_LEAF_GATE_PASS
