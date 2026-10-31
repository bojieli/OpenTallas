#!/bin/bash
# STA + contract only (proof already built by post6.sh)
P=$1; V=${V:-a3e1c}
D=/srv/opentallas-scratch2/claude/hbm-hubmesh-3; W=/srv/opentallas-scratch2/claude/wt/hbm-hubmesh-6
R=$D/post_${V}_$P; PLAN=/srv/opentallas-scratch2/claude/hbm-clkloc-1/in/d44g/die_plan.json
cd $D && (ulimit -v 32000000; PYTHONPATH=$W/tools/die_plan python3 $W/tools/die_plan/die_sta_related.py $R/proof --plan $PLAN --out $R/sta --clock-cell buf --clock-cal none --clock-ocv none --cppr-lca --core-latency-ff 202.5 > $R/sta.log 2>&1)
python3 $W/results/die_hbm_1031/hubmesh2/contract_split.py $R/proof $PLAN 0 40 60 80 120 160 200 260 > $R/contract_split.txt 2>&1
echo POST_DONE
