#!/bin/bash
# Exact gate of the fixed-phase 3:4 stream -> serial transfer ot_s81_vm_x43: aligned run (every serial edge checked),
# two misalignment witnesses + one sample-index-1 schedule witness (fault required), one mutant (the n = 3 bank read
# one serial edge early: must FAIL the aligned run).  Usage: tools/s81_vm/x43_gate.sh OUTDIR
set -u
cd "$(dirname "$0")/../.."
O=${1:?outdir}; mkdir -p "$O"; R=rtl/dsrom_sys/s81_ph; bad=0
iverilog -g2012 -o "$O/sim" -s tb_ot_s81_vm_x43 $R/vm/ot_s81_vm_x43.sv $R/test/tb_ot_s81_vm_x43.sv || exit 2
iverilog -g2012 -DOT_VM_X43_MUT_PHASE -o "$O/mut" -s tb_ot_s81_vm_x43 $R/vm/ot_s81_vm_x43.sv $R/test/tb_ot_s81_vm_x43.sv || exit 2
for m in 0 1 2 3; do vvp -n "$O/sim" +mode=$m > "$O/mode$m.log"; grep -q "TB_X43 PASS mode $m" "$O/mode$m.log" || { echo "GATE FAIL mode $m"; bad=1; }; done
vvp -n "$O/mut" +mode=0 > "$O/mut_phase.log"; grep -q "TB_X43 FAIL mode 0" "$O/mut_phase.log" || { echo "GATE FAIL mutant escaped"; bad=1; }
grep -h "TB_X43" "$O"/*.log
[ $bad = 0 ] && echo "X43_GATE PASS" || { echo "X43_GATE FAIL"; exit 1; }
