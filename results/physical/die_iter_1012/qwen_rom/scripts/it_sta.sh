#!/bin/bash
# qwendie die iteration: re-time a finished die chain's GRT (same SPEF, same clock plan) with an iteration's view libs.
# usage: it_sta.sh <chain run dir R> <iteration libs dir> <tag> <chain tools dir H> [clock plan json]
# (it3+: the plan from tools/budgets/clock_plan.py balance -- view pin insertion + early-tapped trees)
# waits (host-side) for the chain's GRT SPEF, then runs TT setup / FF hold STA into R/sta_r22k_<c>_<tag>.
R=$1; L=$2; TAG=$3; H=$4; PLAN=${5:-}; G=$R/grt_r22k
say(){ echo "$(date -u '+%F %T') UTC [$TAG] $*" | tee -a $R/STATUS_${TAG}.log; }
say "it_sta start libs=$L"
while ! grep -q "full-die GRT exit" $R/STATUS.log 2>/dev/null; do sleep 300; done
[ -s $G/die_grt.spef ] || { say "no die_grt.spef: $(grep 'full-die GRT' $R/STATUS.log | tail -1)"; exit 1; }
for c in tt ff; do D=$R/sta_r22k_${c}_$TAG; mkdir -p $D/libs
  ln -f $G/ckpt_grt.odb $G/route.guide $G/die_grt.spef $D/
  cp $L/qfd_elements_$c.lib $L/qfd_etm_$c.lib $L/views.json $D/libs/
  CP=; [ -s $R/clock/plan.json ] && CP=$R/clock/plan.json; [ -n "$PLAN" ] && CP=$PLAN
  python3 $H/sta_tcl.py r22k $c $D/grt_$c.tcl $CP
  $H/dietop_run.sh $D grt_$c.tcl 8 120
  say "STA $c: $(grep -E '^(wns|tns|worst slack)' $D/grt_$c.log | tr '\n' ' ')"
done
say "it_sta done"
