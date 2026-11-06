#!/bin/bash
# DIE-KV-79: yosys equivalence, A = OLD after synthesis-style constant folding (post.json) vs NEW (post.json);
# B = OLD raw (pre: proc/flatten/memory, no dff folding) vs NEW raw, induction.  usage: eq.sh F
F=$1
for c in A B; do
 if [ $c = A ]; then G=$F/r4g/post.json; T=$F/r4kg/post.json; else G=$F/r4g/pre.json; T=$F/r4kg/pre.json; fi
 cat > $F/eq$c.ys <<YS
read_json $G
rename qkd_hr_core_peer gold
read_json $T
rename qkd_hr_core_peer gate
async2sync
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 4
equiv_induct -seq 4
equiv_status
YS
 yosys -q -l $F/eq$c.log -s $F/eq$c.ys > /dev/null 2>&1; echo "EQ$c rc $?"; grep -A3 "Found [0-9]* \$equiv cells" $F/eq$c.log | head -4
done
