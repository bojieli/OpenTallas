#!/bin/bash
# DIE-HBM-57: one g2.py call per plan for many types; emit PFX_<t>_i<it> probe dirs in $R/g2s for each ITERS
# gen2.sh PLAN PFX "t1,t2" "0 50"
R=/srv/opentallas-scratch2/claude/die-hbm-57; W=/srv/opentallas-scratch2/claude/wt/die-hbm-56
PLAN=$1; PFX=$2; TS=$3; ITS=$4; G=$R/g2gen/$PFX.multi; rm -rf $G
(cd $W && python3 tools/die_plan/g2.py part $PLAN --out $G --types $TS > $G.gen.log 2>&1) || { echo "$PFX GEN FAIL"; exit 1; }
for t in ${TS//,/ }; do for it in $ITS; do N=${PFX}_${t}_i$it; rm -rf $R/g2s/$N; cp -r $G/part_$t $R/g2s/$N
 sed -i "s/congestion_iterations [0-9]*/congestion_iterations $it/" $R/g2s/$N/probe.tcl
 sed -i "s/--name [^ ]*/--name dhbm57-$N/; s/--cpus=8/--cpus=2/" $R/g2s/$N/run.sh; echo "$N ok"; done; done; rm -rf $G
