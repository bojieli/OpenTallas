#!/bin/bash
# HBM-CLKLOC-7: ca.sh on the hub-mesh COMPOSITE proof (cproof), nominal policy (OWNER 12.24b default), d44g plan, wt hbm-clkloc-7.
# landed_phase_ocv (inter-region ports of sb63) -> count_align_plan -> bind -> die_sta_related --count-align (region key)
set -u; ulimit -v 160000000
V=$1; CELL=$2; ST=${3:-clock}; TAG=${4:-$ST}; shift 4 2>/dev/null; XA="$*"; R=/srv/opentallas-scratch2/claude/hbm-clkloc-1; W=/srv/opentallas-scratch2/claude/wt/hbm-clkloc-7; MT=$W/tools/die_plan
D=$R/$V; O=$D/ca7_$TAG; mkdir -p $O; P=$D/${PROOF:-cproof}; PL=$R/in/d44g/die_plan.json
[ -s $O/landed_ocv.json ] || python3 $R/xing_plan.py $PL $R/in/street_part_region.json $O/plan_xing.json > $O/xing.log 2>&1 || exit 1
[ -s $O/landed_ocv.json ] || python3 $W/tools/s81_head/landed_phase_ocv.py $O/plan_xing.json $D/run --tools $MT --clock-cell $CELL --out $O/landed_ocv.json > $O/landed_ocv.log 2>&1 || { echo LOCV_FAIL; tail -3 $O/landed_ocv.log; exit 1; }
cd $MT
python3 count_align_plan.py $O/landed_ocv.json --mc-chips 2000 --sta-proof $P --sta-plan $PL --sta-cppr-lca --sta-core-latency-ff 202.5 --start-tree $ST --start-clean width --sta-clock-cell $CELL $XA --out $O/plan.json > $O/plan.log 2>&1; echo "PLAN_RC $?"
python3 count_align_bind.py $O/plan.json --parts region --out $O/bind.json > $O/bind.log 2>&1; echo "BIND_RC $?"
python3 die_sta_related.py $P --plan $PL --out $O/sta --core-latency-ff 202.5 --count-align $O/bind.json --cppr-lca --hold-buffers HB4 --clock-cell $CELL --nominal-arrival single > $O/sta.log 2>&1; echo "STA_RC $?"
grep -E "COUNT-ALIGN|intra |seam " $O/sta.log | cut -c1-300
