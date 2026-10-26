#!/bin/bash
# TOK-DS/COMP 10-24: owner fold bench on main RTL. run_owner_fold_1024.sh WT OUT
set -uo pipefail
WT=$1; O=$2; mkdir -p $O
cd $WT
git rev-parse HEAD > $O/main_sha.txt
J=8 bash tools/s81_dv/tokfunc/run_owner_fold.sh $WT $O/of > $O/of.log 2>&1; echo "rc $?" >> $O/of.log
for M in 0 2; do python3 -I $WT/tools/verilator_nba_guard.py $O/of/m$M/obj > $O/nba_m$M.txt 2>&1; echo "rc $?" >> $O/nba_m$M.txt; done
echo DONE
