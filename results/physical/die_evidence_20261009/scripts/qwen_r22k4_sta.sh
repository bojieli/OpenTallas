#!/bin/bash
# die-evidence-2: ETM-bound STA (TT setup / FF hold) on the kv-die die_r22k4 full-die GRT SPEF. kv-die's chain times
# assumed element constants only (libs/qfd_elements_*); this re-times the same routed die with the closed-element ETMs
# bound by qwen_die_etm_map against the r22k4 LEF (<out>/libs: qfd_elements + qfd_etm + views.json).
# usage: qwen_r22k4_sta.sh <src> <kv-die die_r22k4> <out>
set -u
SRC=$(readlink -f $1); K=$(readlink -f $2); E=$(readlink -f $3); G=$K/grt_r22k; H=$SRC/tools/qwen_kv_die/chain
ADMIT=/srv/opentallas-scratch/admit.sh
say() { echo "$(date '+%F %T %Z') $*" >> $E/STATUS.log; }
say "waiting for $G/run.exit + die_grt.spef"
until [ -f $G/run.exit ]; do sleep 600; done
[ -f $G/die_grt.spef ] || { say "GRT exit=$(cat $G/run.exit) but NO die_grt.spef: no SPEF-based STA"; exit 1; }
OV=$(awk '/Final congestion report/{f=1} f && /^Total/{print $NF; exit}' $G/grt.log)
say "GRT exit=$(cat $G/run.exit) overflow=${OV:-none} ($(grep -m1 'Total wirelength' $G/grt.log))"
for c in tt ff; do D=$E/sta_r22k_$c; mkdir -p $D/libs
  ln -f $G/ckpt_grt.odb $G/route.guide $G/die_grt.spef $D/ 2>/dev/null || cp $G/ckpt_grt.odb $G/route.guide $G/die_grt.spef $D/
  cp $E/libs/qfd_elements_$c.lib $E/libs/qfd_etm_$c.lib $E/libs/views.json $D/libs/
  ( cd $D && python3 $H/sta_tcl.py r22k $c $D/grt_$c.tcl ) && $ADMIT 120 -- $H/dietop_run.sh $D grt_$c.tcl 8 180 &
done; wait
for c in tt ff; do say "STA $c (GRT SPEF, ETM-bound): $(grep -E '^(wns|tns|worst slack)' $E/sta_r22k_$c/grt_$c.log | tr '\n' ' ')"; done
say "done"
