#!/bin/bash
# QC-CORES-2 btab r8 (COORD RULING BTAB-R7 04:44): k6 Voronoi (r7 planner, OT_R7_BALANCE=0) with NO detour padding
# (--straight L1,L2,L3: every edge at its own shortest legal length) + plan-computed per-branch sizing (su_branch_size,
# 12.8 d1/c) gated by uf_phys3 v1 (OT_PHYS_FIT, COORD RULING MODEL-REFIT-3: TT 250+-9 / FF 202.5+-10 / window <=14).
W=/srv/opentallas-scratch2/claude/wt/qccores2-btab; C=$W/results/qc_su_prog_l1_1026; U=$W/results/qc_cores_btab_r8/su_tree_uf_ls_r7.py
GEO=/srv/opentallas-scratch2/claude/qccores1-btab-1027/plan/btab_m0_r7.geo; LIB=/srv/opentallas-scratch2/claude/qc-su-btab-r5-1026
LEF=$W/physical/asap7_memory_macros_v2
export OT_R7_BALANCE=0 OT_PHYS_FIT=$W/results/model_refit3_1026/uf_phys3_v1.json OT_SIZE_WORKERS=6
cd $W/results/qc_cores_btab_r8/plan
r(){ n=$1; shift; prlimit --as=24000000000 nice python3 -u $C/su_kit_gate.py $n $GEO "$@" > $n.log 2>&1; echo "$n rc $?" >> sweep.txt; }
for k in 5 6 7 8; do r btab_r8_k${k}_np $k $LIB $U $LEF btab_r8_k${k}_np.gate.json --chain --straight L1,L2,L3 --phys --size & done
wait; echo SWEEP_DONE $(date -Is) >> sweep.txt
