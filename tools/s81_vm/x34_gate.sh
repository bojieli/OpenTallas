#!/bin/bash
# Exact gate of the fixed-phase 3:4 serial -> stream transfer ot_s81_vm_x34: aligned run (every stream edge checked),
# two misalignment witnesses (stream one cycle late, serial one cycle late: alignment fault required), one mutant
# (stream reads bank 0 one edge early: must FAIL the aligned run).  Usage: tools/s81_vm/x34_gate.sh OUTDIR
set -u
cd "$(dirname "$0")/../.."
O=${1:?outdir}; mkdir -p "$O"; R=rtl/dsrom_sys/s81_ph; bad=0
iverilog -g2012 -o "$O/sim" -s tb_ot_s81_vm_x34 $R/vm/ot_s81_vm_x34.sv $R/test/tb_ot_s81_vm_x34.sv || exit 2
iverilog -g2012 -DOT_VM_X34_MUT_PHASE -o "$O/mut" -s tb_ot_s81_vm_x34 $R/vm/ot_s81_vm_x34.sv $R/test/tb_ot_s81_vm_x34.sv || exit 2
for m in 0 1 2; do vvp -n "$O/sim" +mode=$m > "$O/mode$m.log"; grep -q "TB_X34 PASS mode $m" "$O/mode$m.log" || { echo "GATE FAIL mode $m"; bad=1; }; done
vvp -n "$O/mut" +mode=0 > "$O/mut_phase.log"; grep -q "TB_X34 FAIL mode 0" "$O/mut_phase.log" || { echo "GATE FAIL mutant escaped"; bad=1; }
grep -h "TB_X34" "$O"/*.log
[ $bad = 0 ] && echo "X34_GATE PASS" || { echo "X34_GATE FAIL"; exit 1; }
