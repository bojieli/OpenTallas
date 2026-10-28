#!/bin/bash
# START-TREE-1 estimate: same die inputs, default (data) vs --start-tree clock. usage: run_die.sh MT OUTDIR XING PROOF PLAN [extra flags...]
MT=$1; O=$2; X=$3; PR=$4; PL=$5; shift 5
mkdir -p $O; cd $O
F="--sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5 $*"
echo "$F" > flags.txt; git -C $MT rev-parse HEAD > tools_sha.txt 2>/dev/null; sha256sum $MT/count_align_plan.py >> tools_sha.txt
python3 $MT/count_align_plan.py $X $F --mc-chips 300 --out base.json > base.log 2>&1; echo "base rc $?" > rc.txt
python3 $MT/count_align_plan.py $X $F --start-tree clock --mc-chips 300 --out clock.json > clock.log 2>&1; echo "clock rc $?" >> rc.txt
echo DONE $(date) >> rc.txt
