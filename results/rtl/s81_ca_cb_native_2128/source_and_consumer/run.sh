#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p gate1
verilator --binary --timing -j 2 -Wno-fatal -Wno-WIDTH --top-module tb --Mdir gate1/obj dsdv_vm_bit.sv dsdv_idx_vmux6.sv selected_source.sv tb.sv > gate1/build.log 2>&1
for scenario in independent native_adjacent equal_adjacent wrong_date; do
 case "$scenario" in
 independent) args='+GAP=2 +EQUAL=0 +MUTDATE=0 +EXPECTFAULT=0';;
 native_adjacent) args='+GAP=1 +EQUAL=0 +MUTDATE=0 +EXPECTFAULT=1';;
 equal_adjacent) args='+GAP=1 +EQUAL=1 +MUTDATE=0 +EXPECTFAULT=0';;
 wrong_date) args='+GAP=2 +EQUAL=0 +MUTDATE=1 +EXPECTFAULT=1';;
 esac
 gate1/obj/Vtb $args > gate1/$scenario.log 2>&1
 tail -5 gate1/$scenario.log
 done
