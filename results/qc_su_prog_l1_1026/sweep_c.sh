#!/bin/bash
# QC-SU-PROG-L1 option (c): r5 gate --phys --size (uf_phys gating + plan-computed per-branch sizing) on the ls+chain prog plans
C=/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/code/results/qc_su_prog_l1_1026; GEO=/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/in/r2/prog_m0.geo; LIB=/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/in/lib; LEF=/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/in/lef; U=/srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/code/results/qc_su_kits/r4/su_tree_uf_ls.py
mkdir -p /srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/sweep_c && cd /srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/sweep_c
r(){ n=$1; shift; prlimit --as=24000000000 python3 -u $C/su_kit_gate.py $n $GEO "$@" > $n.log 2>&1; }
for k in 4 5 6; do
  r c_ls_k${k}_S13 $k $LIB $U $LEF c_ls_k${k}_S13.gate.json --chain --straight L1,L3 --phys --size &
  r c_ls_k${k}_L3 $k $LIB $U $LEF c_ls_k${k}_L3.gate.json --chain --straight L3 --phys --size &
done
python3 -u $C/su_branch_size.py /srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/code/results/qc_su_kits/r3/out/prog_m0_r3.gate.asbuilt.tcl /srv/opentallas-scratch2/claude/qc-su-prog-l1-1026/code/results/qc_su_kits/r3/out/prog_m0_r3.gate.asbuilt.json $GEO $LIB ref_r3_sized.tcl > ref_r3_sized.log 2>&1 &
wait; echo SWEEP_C_DONE
