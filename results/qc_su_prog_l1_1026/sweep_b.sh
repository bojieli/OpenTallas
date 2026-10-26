#!/bin/bash
# QC-SU-PROG-L1 sweep: r5 gate (--phys gating uf_phys, guard band) on (ls) ls-sites and (b) eq-sites, with/without (c) sizing
C=/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/code/results/qc_su_prog_l1_1026; GEO=/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/in/r2/prog_m0.geo; LIB=/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/in/lib; LEF=/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/in/lef
mkdir -p /srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/sweep_b && cd /srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/sweep_b
r(){ n=$1; shift; prlimit --as=16000000000 python3 -u $C/su_kit_gate.py $n $GEO "$@" > $n.log 2>&1; }
r val_ls_k5_S13 5 $LIB /srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/code/results/qc_su_kits/r4/su_tree_uf_ls.py $LEF val_ls_k5_S13.gate.json --trunk 250 --chain --straight L1,L3 --phys &
for k in 5 6 7; do for w in 0.5 1 2; do for st in S13 L3; do
  [ $st = S13 ] && SA="--straight L1,L3" || SA="--straight L3"
  OT_EQ_W=$w r eq_k${k}_w${w}_$st $k $LIB $C/su_tree_uf_eq.py $LEF eq_k${k}_w${w}_$st.gate.json --chain $SA --phys --size &
done; done; done
wait; echo SWEEP_DONE
