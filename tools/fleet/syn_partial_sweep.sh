#!/bin/bash
# HBMc/CHAIN 10-22 06:50: v16_fetch picks the LAST host (sorted) whose syn/<c> has <w>_synth_ff.lib + OT_ETM_DONE_ff, without
# checking <c>.ys / netlist.v; partial ETM-only copies on ot-pve1 (no .ys) won -> FileNotFoundError, r18g S6 died 06:24 (r18e 06:10 same class).
# Move every syn/<c> lacking <c>.ys or <c>.netlist.v to $B/syn_partial_hbmc/ when ANOTHER host holds a complete copy. Usage: B
B=$1; HS="ot-epyc5 ot-epyc7 ot-epyc9 ot-gold1 ot-gold2 ot-pve1"; T=$(mktemp -d)
for h in $HS; do timeout 120 ssh -o ControlPath=none -o ConnectTimeout=15 $h "cd $B/syn 2>/dev/null && for d in */; do d=\${d%/}; if [ -s \$d/\$d.ys ] && [ -s \$d/\$d.netlist.v ]; then echo C \$d; elif [ -z \"\$(find \$d -mmin -20 | head -1)\" ]; then echo P \$d; fi; done" > $T/$h 2>/dev/null; done
cat $T/* | awk '$1=="C"{print $2}' | sort -u > $T/complete
for h in $HS; do P=$(awk '$1=="P"{print $2}' $T/$h | sort | comm -12 - $T/complete | tr '\n' ' ')
  [ -n "${P// /}" ] && timeout 120 ssh -o ControlPath=none $h "mkdir -p $B/syn_partial_hbmc && cd $B/syn && for d in $P; do mv \$d $B/syn_partial_hbmc/ && echo MOVED_PARTIAL $h \$d; done"
  O=$(awk '$1=="P"{print $2}' $T/$h | sort | comm -23 - $T/complete | tr '\n' ' '); [ -n "${O// /}" ] && echo "PARTIAL_NO_COMPLETE $h $O"; done
rm -rf $T
