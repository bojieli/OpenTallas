#!/bin/bash
# ECO-HANDOFF waiter (QC-DRT-ECO-R2 11-26, launched by noprog_watchdog.eco_handoff behind lanes/ECO-HANDOFF.live).  Args: NAME KIT HOST.
# One waiter per kit (mkdir lock).  Waits for the kit's routed 5_2_route.odb (stable > 120 s), starts ONE prd_run ECO-route pass from a fresh dir, measures
# its DRC count against the DRT final count and posts; < 5 % gain = P-ECO-NO-GAIN (no second attempt: the type returns to the die integrator as a structural row).
NAME=$1; KIT=$2; HOST=$3
ROOT=/srv/opentallas-scratch2/claude/QC-DRT-ECO; mkdir -p $ROOT; LOG=$ROOT/$NAME.waiter.log
SO=/srv/opentallas-scratch2/claude/rt/current
say() { echo "$(date '+%F %T') $*" >> $LOG; }
post() { timeout 60 ssh -o BatchMode=yes -o ControlPath=none intel2 "bash ~/coord/bin/post.sh QC-DRT-ECO-R2 \"$(TZ=America/Los_Angeles date '+%F %H:%M') PST WAITER [QC-DRT-ECO-R2 -> QC-INT-R2; cc COORD] $1\"" >> $LOG 2>&1; }
mkdir $ROOT/$NAME.lock 2>/dev/null || { say "lock exists, second waiter refused"; exit 0; }
say "armed $NAME $KIT $HOST"
RS=$(ls -d $KIT/run/results/asap7/*/base); END=$(( $(date +%s) + 259200 ))
until [ -s $RS/5_2_route.odb ] && [ $(( $(date +%s) - $(stat -c %Y $RS/5_2_route.odb) )) -gt 120 ]; do
  [ $(date +%s) -gt $END ] && { say "timeout 72h"; post "$NAME: no routed DB after 72 h, waiter stopped; ECO-route not started."; exit 3; }
  sleep 120
done
# P-ECO-WAITER-RACE (QC-R3-LEC 11-27): run_kit.sh writes 6_final.spef minutes AFTER 5_2_route.odb (cl086d85ba: 03:04:30 vs 03:09:59), and prd_mk.sh
# refuses without it ("lacks 5_2_route.odb / .../6_final.spef").  Wait for the SPEF too (stable 120 s, up to 2 h) before making the ECO pass.
SPEND=$(( $(date +%s) + 7200 ))
until [ -s $RS/6_final.spef ] && [ $(( $(date +%s) - $(stat -c %Y $RS/6_final.spef) )) -gt 120 ]; do
  [ $(date +%s) -gt $SPEND ] && { say "6_final.spef not stable within 2 h of 5_2_route.odb"; break; }
  sleep 30
done
LG=$(ls -t $KIT/run/logs/asap7/*/base/5_2_route*.log | head -1)
N=$(grep -h "Completing 100%" $LG | tail -1 | sed 's/.*with //; s/ violations.*//')
say "routed DB ready: $RS/5_2_route.odb final: $N"
OUT=$ROOT/${NAME}_eco_$(date +%m%d%H%M)
export OT_PRD_FROM=route
if OUT_MSG=$(bash $SO/tools/die_plan/post_route_drv/prd_mk.sh $KIT $OUT t0 $SO 2>&1); then
  say "prd_mk ok $OUT"
  post "$NAME: DRT ended at $N violations. ECO-route attempt 1 of 1 started from fresh dir $OUT on $HOST (prd_run, route-keeping)."
  ( cd $OUT && ot-run --mem 48 --threads 8 --dir $OUT --hosts $HOST -- bash $SO/tools/die_plan/post_route_drv/prd_run.sh $OUT 8 48 > $OUT/ot_run.log 2>&1 )
  say "ECO ot-run ended rc=$?"
  LG2=$(ls -t $OUT/run/logs/asap7/*/base/5_2_route*.log 2>/dev/null | head -1)
  M=$(grep -h "Completing 100%" $LG2 2>/dev/null | tail -1 | sed 's/.*with //; s/ violations.*//')
  if [ -z "$M" ]; then post "$NAME: ECO attempt 1 ended with no readable route count (see $OUT/ot_run.log, $OUT/prd_result.json); no second attempt."; exit 0; fi
  V=$(awk -v n="$N" -v m="$M" 'BEGIN{ if (m==0) print "CLOSED"; else if (n>0 && (n-m)/n >= 0.05) print "GAIN"; else print "NOGAIN" }')
  case $V in
    CLOSED) post "$NAME: ECO attempt 1 DRC 0 (base $N). Route DB $OUT; sign-off chain is next for the kit owner.";;
    GAIN)   post "$NAME: ECO attempt 1 DRC $N -> $M (gain >= 5 %). Route DB $OUT; the owner decides on one more pass.";;
    *)      post "$NAME: ECO attempt 1 DRC $N -> $M (gain < 5 %): class P-ECO-NO-GAIN. ECO loop stops; type returns to QC-INT-R2 as a structural row.";;
  esac
else
  say "prd_mk refused: $OUT_MSG"
  post "$NAME: DRT ended at $N violations. ECO-route NOT started: prd_mk refused: $(echo $OUT_MSG | tr -d '\"' | cut -c1-300). Routed DB retained for a hand ECO."
fi
