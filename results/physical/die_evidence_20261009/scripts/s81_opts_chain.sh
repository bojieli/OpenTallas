#!/bin/bash
# die-evidence-2 2026-10-09 (copy of tools/s81/s81_dies_chain.sh, s81-dies 2026-10-08): the chain for an S81 OPTIONS FILE
# m221pq layer1 chains (mk_chain5.sh): real case (generator) -> own clock plan (clock-only CTS, tools/budgets/clock_plan.py)
# -> balanced STA kit (tools/s81/die_sta.py, the die's own plan) -> place (OpenROAD real case) -> FULL-die GRT k=1 ->
# GRT-parasitic die STA TT / FF / SS (dietop_grt_sta.sh).  Every heavy step goes through the host admission guard
# (memory-gated, /srv/opentallas-scratch/admit.sh).  Usage (on the host, detached):
#   s81_opts_chain.sh <options file> <generator --die kind> <src checkout> <run dir> [threads]
set -euo pipefail
OPTF=$(readlink -f $1); KIND=$2; S=$(readlink -f $3); M=$4; T=${5:-24}; NAME=$(basename $M)
if [ -d "$M" ] && [ -n "$(find "$M" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  echo "Refusing to overwrite existing die evidence: $M" >&2; exit 2
fi
mkdir -p "$M"; M=$(readlink -f "$M"); cd "$S"
CLOCK_FLAGS=()
[ "${OT_S81_CLOCK_FAMILIES:-0}" = 1 ] && CLOCK_FLAGS+=(--s81-local-families)
export OT_S81_Q_LEF=physical/s81_die_views/q_elem_qs5f/q_elem.lef.gz
A="$(cat $OPTF)"; echo "$A" > $M/options.txt
AK=$(echo "$A" | sed "s/--die $KIND//")
st(){ echo "$(date -u +%FT%TZ) $*" >> $M/STATUS.log; }
st "start $NAME src $(cat $S/SOURCE_SHA 2>/dev/null)"
/srv/opentallas-scratch/admit.sh 40 -- python3 tools/dsrom_s81_fulldie.py real $A --work $M/a_real > $M/real_gen.log 2>&1 || { st GEN_FAIL; exit 1; }
st GEN_DONE
# own clock plan (the generator's die kind: s81r8_layer = scan, s81r8_head)
C=$M/clock; mkdir -p $C
( /srv/opentallas-scratch/admit.sh 40 -- python3 tools/budgets/extract_die.py --src $S --die s81r8_$KIND --s81-opts "$AK" --out $C/model.json.gz > $C/extract.log 2>&1 || { st CLOCK_EXTRACT_FAIL; exit 1; }
  clock_pids=()
  for g in htop hreg region; do
    python3 tools/budgets/clock_plan.py emit "${CLOCK_FLAGS[@]}" --die-model $C/model.json.gz --group $g --name ${NAME}_$g --out $C/$g > $C/emit_$g.log 2>&1
    (cd $C/$g && /srv/opentallas-scratch/admit.sh 24 -- bash run.sh > run.out 2>&1) &
    clock_pids+=("$!")
  done
  for clock_pid in "${clock_pids[@]}"; do
    wait "$clock_pid" || { st CLOCK_CTS_FAIL; exit 1; }
  done
  python3 tools/budgets/clock_plan.py record "${CLOCK_FLAGS[@]}" --die-model $C/model.json.gz --case $C/htop --case $C/hreg --case $C/region --out $C/plan.json > $C/record.log 2>&1 || { st CLOCK_RECORD_FAIL; exit 1; }
  gzip -kf $C/plan.json
  st "CLOCK_PLAN $(test -f $C/plan.json.gz && echo done || echo failed)"
  CP=$C/plan.json.gz; [ -s "$CP" ] || { st CLOCK_PLAN_MISSING; exit 1; }
  rm -rf $M/kit; mkdir -p $M/kit
  /srv/opentallas-scratch/admit.sh 60 -- python3 tools/s81/die_sta.py kit --gen-root $S --views-root $S --s81-opts "$AK" --die $KIND \
      --out $M/kit --clock-plan $CP --index-out $M/kit/index.json > $M/kit/kit.log 2>&1 || { rc=$?; echo "$rc" > $M/kit/kit.exit; st KIT_FAIL; exit "$rc"; }
  echo 0 > $M/kit/kit.exit
  echo $S > $M/kit/src_root; echo $CP > $M/kit/clock_plan_used; st "KIT rc=$(cat $M/kit/kit.exit) plan $CP" ) &
CLOCK_PID=$!
# place the real case
D=$M/a_real; date -u +%FT%TZ > $D/run.log.start
/srv/opentallas-scratch/admit.sh 40 -- docker run --rm --name s81dies_${NAME}_place --cpus=$T -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $T -no_init -exit /work/run.tcl > /work/run.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc" || { rc=$?; echo "$rc" > $D/run.log.exit; st PLACE_FAIL; wait "$CLOCK_PID" || true; exit "$rc"; }
echo 0 > $D/run.log.exit; date -u +%FT%TZ > $D/run.log.end
st "PLACE rc=$(cat $D/run.log.exit)"
wait "$CLOCK_PID" || { st CLOCK_OR_KIT_FAIL; exit 1; }
[ "$(cat $D/run.log.exit)" = 0 ] || { st PLACE_FAIL; exit 1; }
[ "$(cat $M/kit/kit.exit 2>/dev/null)" = 0 ] || { st KIT_FAIL; exit 1; }
cd $M && /srv/opentallas-scratch/admit.sh 120 -- $S/physical/s81_die_views/dietop/dietop_grt_sta.sh a_real grt kit 48 400 || { st GRT_STA_FAIL; exit 1; }
for c in tt ff ss; do echo "$c $(grep -E "^(worst slack|tns)" $M/grt/sta_$c.log | tr "\n" " ")"; done > $M/grt/summary.txt
st "CHAIN_DONE $(tr '\n' ' ' < $M/grt/summary.txt)"
