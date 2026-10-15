#!/bin/bash
set -eu
S=$1;O=$2;TOP=${3:-tb_dsfd_vm_static_wstage128};MUT=${4:-OT_VM_WSTAGE_MUT_TAG};INPUT=${5:-staging_inputs};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
build(){ "$V" --binary --timing -O1 -Wno-fatal -j 2 --top-module "$TOP" --Mdir "$O/obj_$1" -o tb ${2:-} "$S/dsfd_vm_static_wstage128.sv" "$S/$TOP.sv" "$S/dsfd_vm_static_wdispatch128.sv" "$S/dsfd_vm_static_rscatter.sv" "$S/dsfd_vm_static_scatter.sv" "$S/dsfd_vm_static_bank128.sv" "$S/dsfd_vm_static_relay128.sv" "$S/dsfd_vm_static_slice128_rel2.sv" "$S/ot_sram_1r1w_512x128_m4_r2c2.v" > "$O/build_$1.log" 2>&1; }
build base & p1=$!;build mutant "+define+$MUT" & p2=$!;wait "$p1";wait "$p2"
for l in L0 L2 L14 L20;do
 for c in base mutant;do "$O/obj_$c/tb" +TRACE="$S/$INPUT/$l.txt" +END=36000 > "$O/run_${l}_${c}.log" 2>&1;head -2 "$O/run_${l}_${c}.log";done
 grep -qx PASS "$O/run_${l}_base.log";grep -qx FAIL "$O/run_${l}_mutant.log"
done
echo STATIC_WSTAGE_GATE_PASS
