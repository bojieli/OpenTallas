#!/bin/bash
# HBM-B-RTL1: SU scalar tree lockstep (tb_hbm_su_stree: tree vs d4f RF_RELAY=36 relay network and vs RF_RELAY=L_TREE).
# usage: run_stree_lockstep.sh <outdir> [MUT=0] [NCYC=4000] [UP=14] [DN=14]   -> prints "STREE PASS|FAIL ..."
set -u
O=${1:?outdir}; MUT=${2:-0}; NCYC=${3:-4000}; UP=${4:-14}; DN=${5:-14}
D=$(cd "$(dirname "$0")" && pwd); mkdir -p "$O"
iverilog -g2012 -Ptb_hbm_su_stree.MUT=$MUT -Ptb_hbm_su_stree.NCYC=$NCYC -Ptb_hbm_su_stree.UP=$UP -Ptb_hbm_su_stree.DN=$DN \
  -o "$O/stree.vvp" -s tb_hbm_su_stree "$D/tb_hbm_su_stree.sv" "$D/ot_hbm_su_stree.sv" || { echo "STREE FAIL compile"; exit 2; }
vvp -n "$O/stree.vvp" | tee "$O/stree.log" | tail -12
grep -q "^STREE PASS" "$O/stree.log"
