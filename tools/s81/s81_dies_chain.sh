#!/bin/bash
# s81-dies 2026-10-08: die-evidence chain for one S81 recipe of tools/s81/s81_dies_recipe.py (scan / head*), as the
# m221pq layer1 chains (mk_chain5.sh): real case (generator) -> own clock plan (clock-only CTS, tools/budgets/clock_plan.py)
# -> balanced STA kit (tools/s81/die_sta.py, the die's own plan) -> place (OpenROAD real case) -> FULL-die GRT k=1 ->
# GRT-parasitic die STA TT / FF / SS (dietop_grt_sta.sh).  Every heavy step goes through the host admission guard
# (memory-gated, /srv/opentallas-scratch/admit.sh).  Usage (on the host, detached):
#   s81_dies_chain.sh <recipe name> <generator --die kind> <src checkout> <run dir> [threads]
set -u
NAME=$1; KIND=$2; S=$(readlink -f $3); M=$4; T=${5:-24}
mkdir -p $M; M=$(readlink -f $M); cd $S
export OT_S81_Q_LEF=physical/s81_die_views/q_elem_qs5f/q_elem.lef.gz
A="$(python3 tools/s81/s81_dies_recipe.py opts $NAME)"; echo "$A" > $M/options.txt
AK=$(echo "$A" | sed "s/--die $KIND//")
st(){ echo "$(date -u +%FT%TZ) $*" >> $M/STATUS.log; }
st "start $NAME src $(cat $S/SOURCE_SHA 2>/dev/null)"
/srv/opentallas-scratch/admit.sh 40 -- python3 tools/dsrom_s81_fulldie.py real $A --work $M/a_real > $M/real_gen.log 2>&1 || { st GEN_FAIL; exit 1; }
st GEN_DONE
# own clock plan (the generator's die kind: s81r8_layer = scan, s81r8_head)
C=$M/clock; mkdir -p $C
( /srv/opentallas-scratch/admit.sh 40 -- python3 tools/budgets/extract_die.py --src $S --die s81r8_$KIND --s81-opts "$AK" --out $C/model.json.gz > $C/extract.log 2>&1 || { st CLOCK_EXTRACT_FAIL; exit 1; }
  for g in htop hreg region; do
    python3 tools/budgets/clock_plan.py emit --die-model $C/model.json.gz --group $g --name ${NAME}_$g --out $C/$g > $C/emit_$g.log 2>&1
    (cd $C/$g && /srv/opentallas-scratch/admit.sh 24 -- bash run.sh > run.out 2>&1) &
  done
  wait
  python3 tools/budgets/clock_plan.py record --die-model $C/model.json.gz --case $C/htop --case $C/hreg --case $C/region --out $C/plan.json > $C/record.log 2>&1 && gzip -kf $C/plan.json
  st "CLOCK_PLAN $(test -f $C/plan.json.gz && echo done || echo failed)"
  CP=$C/plan.json.gz; [ -f $CP ] || CP=$(ls /srv/opentallas-scratch/claude/s81-die/m221pq_r3/clock/plan.json.gz 2>/dev/null)
  rm -rf $M/kit; mkdir -p $M/kit
  /srv/opentallas-scratch/admit.sh 60 -- python3 tools/s81/die_sta.py kit --gen-root $S --views-root $S --s81-opts "$AK" --die $KIND \
      --out $M/kit --clock-plan $CP --index-out $M/kit/index.json > $M/kit/kit.log 2>&1; echo $? > $M/kit/kit.exit
  echo $S > $M/kit/src_root; echo $CP > $M/kit/clock_plan_used; st "KIT rc=$(cat $M/kit/kit.exit) plan $CP" ) &
# place the real case
D=$M/a_real; date -u +%FT%TZ > $D/run.log.start
/srv/opentallas-scratch/admit.sh 40 -- docker run --rm --name s81dies_${NAME}_place --cpus=$T -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $T -no_init -exit /work/run.tcl > /work/run.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
echo $? > $D/run.log.exit; date -u +%FT%TZ > $D/run.log.end
st "PLACE rc=$(cat $D/run.log.exit)"
wait
[ "$(cat $D/run.log.exit)" = 0 ] || { st PLACE_FAIL; exit 1; }
[ "$(cat $M/kit/kit.exit 2>/dev/null)" = 0 ] || { st KIT_FAIL; exit 1; }
cd $M && /srv/opentallas-scratch/admit.sh 120 -- $S/physical/s81_die_views/dietop/dietop_grt_sta.sh a_real grt kit 48 400
for c in tt ff ss; do echo "$c $(grep -E "^(worst slack|tns)" $M/grt/sta_$c.log | tr "\n" " ")"; done > $M/grt/summary.txt
st "CHAIN_DONE $(tr '\n' ' ' < $M/grt/summary.txt)"
