#!/bin/bash
set -eu
S=$1;O=$2;TOP=${3:-tb_dsfd_vm_static512};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
build(){ "$V" --binary --timing -O1 -Wno-fatal -j 2 --top-module "$TOP" --Mdir "$O/obj_$1" -o tb ${2:-} "$S/dsfd_vm_static_rscatter.sv" "$S/dsfd_vm_static_scatter.sv" "$S/dsfd_vm_static_bank128.sv" "$S/dsfd_vm_static_slice128.sv" "$S/dsfd_vm_static_return.sv" "$S/dsfd_vm_static512.sv" "$S/dsfd_vm_static_relay128.sv" "$S/dsfd_vm_static_slice128_rel2.sv" "$S/dsfd_vm_static512_rel2.sv" "$S/ot_sram_1r1w_512x128_m4_r2c2.v" "$S/$TOP.sv" > "$O/build_$1.log" 2>&1; }
build base & p1=$!;build mutant +define+OT_VM_512_MUT_SWAP_SLICES & p2=$!;wait "$p1";wait "$p2"
for c in base mutant;do "$O/obj_$c/tb" > "$O/run_$c.log" 2>&1;head -2 "$O/run_$c.log";done
grep -qx PASS "$O/run_base.log";grep -qx FAIL "$O/run_mutant.log"
echo STATIC512_GATE_PASS
