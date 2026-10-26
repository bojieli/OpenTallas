#!/bin/bash
# HEAD-CORE-LAT-R2 c3' pushdown proofs (a) placement/dont_touch, (b) ETM ft arcs vs flat TT/FF, (c) M5 ft pins reachable
# from M9 (die-like GRT+DRT on the core abstract).  $1 = trial dir (has quad.json + run/), output -> $1/proof
set -uo pipefail
K=$(realpath "$1"); NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' $K/config.mk); P=$K/proof; mkdir -p $P
ODB=/work/run/results/asap7/$NICK/base/4_cts.odb; IMG=openroad/orfs:asap7lock; N=hclp-$(basename $K)-$$
PLAN=$(python3 -c "import json;q=json.load(open('$K/quad.json'));print(' '.join('%s:%s:%.3f:%.3f'%tuple(c[:4]) for c in q['die_cells']))")
run() { docker run --rm --name $N-$1 --cpus=4 --memory=16g --memory-swap=16g -v "$K":/work -v "$P":/out "${@:2}"; }
run a -e ODB=$ODB -e "PLAN=$PLAN" $IMG bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/pushdown_place_check.tcl' > $P/a.log 2>&1
for C in TT FF; do for PH in flat etm; do
run b$C$PH -e OT_CORNER=$C -e PHASE=$PH -e ODB=$ODB -e OUT=/out $IMG bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /out; openroad -exit /work/pushdown_etm_check.tcl' > $P/b_${C}_$PH.log 2>&1
done; done
run c -e OUT=/out $IMG bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /out; openroad -exit /work/pushdown_reach.tcl' > $P/c.log 2>&1
grep -h -E 'PA_RESULT|ETM_|REACH_RESULT|Error' $P/*.log
