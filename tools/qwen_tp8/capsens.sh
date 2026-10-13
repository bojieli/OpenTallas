#!/bin/bash
# qwen-tp8/die: die STA routed-cap sensitivity (results/physical/die_region_drt_1012/README.md: routed RCX net cap vs GRT
# median +40 %, p95 +144 %).  Re-times the finished die_chain STA dirs (sta_<die>_<c>) with every SPEF cap x1.40 / x2.44.
# usage: capsens.sh DIE RUN_DIR KIT_DIR   (after die_chain.sh DIE RUN_DIR KIT_DIR)
set -u
DIE=$1; R=$(readlink -f $2); K=$(readlink -f $3); H=$K/tools/qwen_kv_die/chain
ADMIT=/srv/opentallas-scratch/admit.sh; P4=110
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
for f in 1.40 2.44; do for c in tt ff; do
  S=$R/sta_${DIE}_$c; D=$R/sta_${DIE}_${c}_cap${f/./}
  [ -s $S/die_grt.spef ] || { say "capsens $f $c: no $S/die_grt.spef"; continue; }
  mkdir -p $D && cp -r $S/libs $D/ && cp $S/grt_$c.tcl $D/ && ln -f $S/ckpt_grt.odb $S/route.guide $D/ 2>/dev/null
  python3 $K/tools/qwen_tp8/spef_scale.py $S/die_grt.spef $D/die_grt.spef $f
  cp "$S"/clock_*.tcl "$D"/
  sed -i "s#$S#$D#g" $D/grt_$c.tcl
  $ADMIT $P4 -- $H/dietop_run.sh $D grt_$c.tcl 8 $((P4+60))
  [ "$(cat "$D/run.exit")" = 0 ] || { say "capsens x$f STA $c FAILED: run.exit $(cat "$D/run.exit")"; exit 1; }
  say "capsens x$f STA $c: $(grep -E '^(wns|tns|worst slack)' $D/grt_$c.log | tr '\n' ' ')"
done; done
say "capsens done"
