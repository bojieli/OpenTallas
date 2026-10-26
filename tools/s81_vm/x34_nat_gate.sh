#!/bin/bash
# claude S81 VM F2 2026-10-15: exact gate of the native (NAT=1) 3:4 transfer: ICG-gated serial banks, captured stream
# side one stream edge later.  Aligned run (every stream edge checked at +1), two misalignment witnesses (fault
# required), stream-phase mutant and serial-bank mutant must FAIL the aligned run.  Usage: x34_nat_gate.sh OUTDIR
set -u
cd "$(dirname "$0")/../.."
O=${1:?outdir}; mkdir -p "$O"; R=rtl/dsrom_sys/s81_ph; bad=0
iverilog -g2012 -Ptb_ot_s81_vm_x34.NAT=1 -Ptb_ot_s81_vm_x34.BAL=${X34_BAL:-1} -o "$O/sim" -s tb_ot_s81_vm_x34 $R/vm/ot_s81_vm_x34.sv $R/test/tb_ot_s81_vm_x34.sv || exit 2
iverilog -g2012 -Ptb_ot_s81_vm_x34.NAT=1 -Ptb_ot_s81_vm_x34.BAL=${X34_BAL:-1} -DOT_VM_X34_MUT_PHASE -o "$O/mut" -s tb_ot_s81_vm_x34 $R/vm/ot_s81_vm_x34.sv $R/test/tb_ot_s81_vm_x34.sv || exit 2
iverilog -g2012 -Ptb_ot_s81_vm_x34.NAT=1 -Ptb_ot_s81_vm_x34.BAL=${X34_BAL:-1} -DOT_VM_X34_MUT_SBANK -o "$O/muts" -s tb_ot_s81_vm_x34 $R/vm/ot_s81_vm_x34.sv $R/test/tb_ot_s81_vm_x34.sv || exit 2
for m in 0 1 2; do vvp -n "$O/sim" +mode=$m > "$O/mode$m.log"; grep -q "TB_X34 PASS mode $m" "$O/mode$m.log" || { echo "GATE FAIL mode $m"; bad=1; }; done
vvp -n "$O/mut" +mode=0 > "$O/mut_phase.log"; grep -q "TB_X34 FAIL mode 0" "$O/mut_phase.log" || { echo "GATE FAIL phase mutant escaped"; bad=1; }
vvp -n "$O/muts" +mode=0 > "$O/mut_sbank.log"; grep -q "TB_X34 FAIL mode 0" "$O/mut_sbank.log" || { echo "GATE FAIL sbank mutant escaped"; bad=1; }
grep -h "TB_X34" "$O"/*.log
[ $bad = 0 ] && echo "X34_NAT_GATE PASS" || { echo "X34_NAT_GATE FAIL"; exit 1; }
