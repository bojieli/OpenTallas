#!/bin/bash
# qwendie-1012: re-time an existing die GRT (ckpt_grt.odb + die_grt.spef) with a clock plan, TT setup + FF hold.
# usage: sta_tag.sh <run dir R> <tools dir H (chain/)> <plan.json> <tag> <kv|r22k> [libs dir, default R/libs]
# GRT from R/grt_<die>; results R/sta_<die>_<c>_<tag>; one line per corner in R/STATUS_<tag>.log.  The clock-path OCV
# bound (sta_tcl.py: per-sink non-shared part + region-pair inter-clock uncertainty) is ON; OT_STA_OCV=0 only for parity.
set -u; R=$1; H=$2; PLAN=$3; TAG=$4; DIE=$5; LIB=${6:-$R/libs}; G=$R/grt_$DIE; ADMIT=/srv/opentallas-scratch/admit.sh
say() { echo "$(date "+%F %T %Z") [$TAG] $*" >> $R/STATUS_$TAG.log; }
say "start plan=$PLAN libs=$LIB ocv=${OT_STA_OCV:-0.05}"
for c in tt ff; do D=$R/sta_${DIE}_${c}_$TAG; mkdir -p $D/libs
  ln -f $G/ckpt_grt.odb $G/die_grt.spef $D/
  cp $LIB/qfd_elements_$c.lib $D/libs/; for f in $LIB/qfd_etm_$c.lib $LIB/views.json $LIB/qfd_etm_*_$c.lib $LIB/ot_hbm3e_phy_$c.lib; do [ -f "$f" ] && cp "$f" $D/libs/; done
  python3 $H/sta_tcl.py $DIE $c $D/grt_$c.tcl $PLAN
  $ADMIT 60 -- $H/dietop_run.sh $D grt_$c.tcl 8 100
  say "STA $c: $(grep -E "^(wns|tns|worst slack)" $D/grt_$c.log | tr "\n" " ") | $(grep -h -e OT_CLOCK_OCV -e OT_CLOCK_PLAN -e OT_STEP_FAIL $D/grt_$c.log | tr "\n" " ")"
done
say done
