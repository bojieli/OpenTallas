#!/bin/bash
# kv-die: re-run die STA TT/FF on an existing GRT with a CTS clock plan.
# usage: kvi_sta_plan.sh <run dir R> <chain tools dir H> [plan json] [sta dir tag]
# (qwendie-1012: pass the clock_plan.py balance output -- view pin insertion -- as the plan; tag keeps earlier STA dirs)
set -u; R=$1; H=$2; PLAN=${3:-$1/clock/plan.json}; TAG=${4:-p}; DIE=kv; G=$R/grt_$DIE; ADMIT=/srv/opentallas-scratch/admit.sh
say() { echo "$(date "+%F %T %Z") $*" >> $R/STATUS.log; }
for c in tt ff; do D=$R/sta_${DIE}${TAG}_$c; mkdir -p $D/libs
  ln -f $G/ckpt_grt.odb $G/route.guide $G/die_grt.spef $D/
  cp $R/libs/qfd_elements_$c.lib $D/libs/; [ -f $R/libs/qfd_etm_$c.lib ] && cp $R/libs/qfd_etm_$c.lib $R/libs/views.json $D/libs/; for f in $R/libs/qfd_etm_*_$c.lib; do [ -f "$f" ] && cp "$f" $D/libs/; done
  python3 $H/sta_tcl.py $DIE $c $D/grt_$c.tcl $PLAN
  $ADMIT 40 -- $H/dietop_run.sh $D grt_$c.tcl 8 100
  say "STA(plan $TAG) $c: $(grep -E "^(wns|tns|worst slack)" $D/grt_$c.log | tr "\n" " ")"
done
