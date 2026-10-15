#!/bin/bash
set -eu
S=$1
O=$2
V=${VERILATOR:-verilator}
mkdir -p "$O"
for c in base mutant; do
 define=;if [ "$c" = mutant ];then define=+define+OT_VM_W0_MUT_SLICE;fi
 "$V" --binary --timing -O1 -Wno-fatal -j 4 --top-module tb_dsfd_vm_static_wsched_roots --Mdir "$O/obj_$c" -o tb $define "$S/dsfd_vm_static_w0.sv" "$S/dsfd_vm_static_wcontrol.sv" "$S/dsfd_vm_static_wsched.sv" "$S/dsfd_vm_static_wdispatch128.sv" "$S/dsfd_vm_static_wstage128.sv" "$S/tb_dsfd_vm_static_wsched_roots.sv" > "$O/build_$c.log" 2>&1
 "$O/obj_$c/tb" > "$O/run_$c.log" 2>&1
 tail -3 "$O/run_$c.log"
done
"$O/obj_base/tb" +mode=1 > "$O/run_clock_fault.log" 2>&1
grep -qx PASS "$O/run_base.log"
grep -qx FAIL "$O/run_mutant.log"
grep -qx CLOCK_FAULT_PASS "$O/run_clock_fault.log"
echo WRITE_ROOTS_GATE_PASS
