#!/bin/bash
# VL2QC-STA: for each private item wait for the kit_wave run-item result.json; on PASS: (1) posguard.py on the kit
# (plan core xy/orient, strap sites, grt mode/image, flow tag) on epyc9, (2) copy flow_tag/grt_transition_mode into K,
# (3) rsync the gen dir epyc9 -> the item's route host, (4) route + sign-off there through ot-run-wave
# (run_kit.sh K route 48 8). Route hosts (COORD 11-12): spread over epyc7/epyc8/intel1, epyc2 OUT (disk), not epyc9.
# Host per item: RHMAP="item=host ..." entries win, else round-robin over RHS (default "epyc7 epyc8 intel1").
# Logs: sta/route_after_place.log, sta/spec/<it>/{posguard.log,rsync.log,route.otrun.log}. Hub-side (intel2).
set -u; cd /
W=/srv/opentallas-scratch2/claude/vislayout2-qc
RHS=(${RHS:-epyc7 epyc8 intel1})
ITEMS="$*"
declare -A DONE=() HOST=()
i=0; for it in $ITEMS; do HOST[$it]=${RHS[$((i % ${#RHS[@]}))]}; i=$((i+1)); done
for kv in ${RHMAP:-}; do HOST[${kv%%=*}]=${kv#*=}; done
for it in $ITEMS; do
  case ${HOST[$it]} in epyc2|epyc9) echo "refusing route host ${HOST[$it]} for $it" >&2; exit 2;; esac
  echo "$(date '+%F %T %Z') $it route host ${HOST[$it]}" >> $W/sta/route_after_place.log
done
n=$(echo $ITEMS | wc -w)
while [ ${#DONE[@]} -lt $n ]; do
  for it in $ITEMS; do
    [ -n "${DONE[$it]:-}" ] && continue
    R=$W/sta/spec/$it/result.json; [ -s $R ] || continue
    v=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1])).get('verdict'))" $R)
    echo "$(date '+%F %T %Z') $it result $v" >> $W/sta/route_after_place.log
    DONE[$it]=1
    [ "$v" = PASS ] || continue
    RH=${HOST[$it]}
    G=$W/sta/runs/a/items/$it/attempt_1/gen
    ssh -n -o ControlPath=none epyc9 "for f in flow_tag grt_transition_mode; do cp $G/\$f $G/$it/\$f; done; cd $W && python3 -I -B posguard.py sta/por/plan_vl2_sta_a.json $it $G/$it" > $W/sta/spec/$it/posguard.log 2>&1
    pg=$?
    echo "$(date '+%F %T %Z') $it posguard rc $pg: $(head -1 $W/sta/spec/$it/posguard.log)" >> $W/sta/route_after_place.log
    [ $pg -eq 0 ] || continue
    ( ssh -n -o ControlPath=none epyc9 "ssh -n -o BatchMode=yes -o ControlPath=none $RH mkdir -p $G && rsync -a $G/ $RH:$G/" > $W/sta/spec/$it/rsync.log 2>&1
      echo "RSYNC_RC=$?" >> $W/sta/spec/$it/rsync.log
      /home/ubuntu/.local/lib/kw44/ot-run-wave --mem 48 --threads 8 --dir $G/$it --stage $G/$it --stage $G/run_kit.sh --hosts $RH -- bash -c "export OT_GRT_TRANSITION_MODE=edge_outline OT_FLOW_TAG=flow-20261108-ef-qc; bash $G/run_kit.sh $G/$it route 48 8" > $W/sta/spec/$it/route.otrun.log 2>&1
      echo "ROUTE_RC=$?" >> $W/sta/spec/$it/route.otrun.log
      echo "$(date '+%F %T %Z') $it route done on $RH" >> $W/sta/route_after_place.log ) &
  done
  sleep 60
done
wait
echo "$(date '+%F %T %Z') all done" >> $W/sta/route_after_place.log
