#!/bin/bash
# MODEL-REFIT-2 prog re-plan sweep: su_tree_uf_ls (legal island sites) + su_kit_gate r4 --chain on the MIF0 prog placement
P=/srv/opentallas-scratch2/claude/model-refit2-1026/plan; LIB=/srv/opentallas-scratch2/claude/master-plan-r4-1026/su_refloor; G=$P/r4/su_kit_gate.py; U=$P/r4/su_tree_uf_ls.py
mkdir -p $P/sweep && cd $P/sweep
r(){ n=$1; shift; prlimit --as=16000000000 python3 -u $G $n "$@" > $n.log 2>&1; }
for k in 4 5 6 7; do for st in pin L3; do
 r prog_ls_k${k}_${st} $P/r2/prog_m0.geo $k $LIB $U $P/lef prog_ls_k${k}_${st}.gate.json --trunk 250 --chain $( [ $st = pin ] || echo --straight $st ) &
done; done
wait; echo SWEEP_DONE
