#!/bin/bash
# price.sh <plan_dir> <tag>: R12 price chain (lane traversal + hub cc legs, S2 schedule) t_banks -> plan
W=/srv/opentallas-scratch2/claude/wt/path-hbm-r13-1026; TB=/srv/opentallas-scratch2/claude/path-hbm-r8-1026/t_banks
R=$W/results/path_hbm_r12; D=/srv/opentallas-scratch2/claude/hbm-unified-1-1026/price; mkdir -p $D
P=$1; T=$2; export PYTHONPATH=$W/tools/die_plan:$W/tools
cd $W && python3 tools/hbm_b2/b1_lane_traversal.py price --baseline $TB --candidate $P --out $D/${T}_lane.json --no-schedule > $D/${T}_lane.log 2>&1 || { echo LANEFAIL; exit 1; }
python3 $R/cc_price.py $W $TB $P $D/${T}_lane.json $D/${T}_cc.json > $D/${T}_cc.log 2>&1 || { echo CCFAIL; exit 1; }
python3 $R/combine.py $W $D/${T}_lane.json $D/${T}_cc.json $D/${T}_price.json > $D/${T}_comb.log 2>&1 || { echo COMBFAIL; exit 1; }
python3 /srv/opentallas-scratch2/claude/path-hbm-r13-1026/decomp.py $W $D/${T}_lane.json $D/${T}_cc.json > $D/${T}_decomp.json 2>$D/${T}_decomp.err
python3 -c "
import json;d=json.load(open('$D/${T}_price.json'));print('$T', {w:{m:d[w][m]['loss_pct'] for m in ('lower','mid_sm_serial','upper')} for w in d})"
