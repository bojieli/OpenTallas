#!/bin/bash
# lane.sh HOST LANEFILE -- run the lane's jobs one after another on HOST through remote_gate (every other worker
# excluded).  LANEFILE lines: WORKTREE|MIN_GB|LOGFILE|FETCH_DIR_OR_-|command...
H=$1; F=$2
ALL="ot-pve1 ot-pve2 ot-pve3 155.103.253.78 155.103.253.133 155.103.253.191 155.103.253.16 155.103.253.39 155.103.253.114"
EX=$(for h in $ALL; do [ $h != $H ] && echo -n "$h,"; done)
SSHO="-i /home/ubuntu/.ssh/agidock_ot -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
while IFS='|' read -r WT G LOG FETCH CMD; do
  [ -z "$WT" ] && continue; case $WT in \#*) continue;; esac
  echo "$(date -Is) START $CMD" >> $F.progress
  (cd $WT && OT_PHYSICAL_WORK_ROOT=/home/ubuntu/w15work OT_GATE_MIN_GB=$G OT_GATE_EXCLUDE=$EX /tmp/claude-1000/remote_gate.py $CMD > $LOG 2>&1 < /dev/null)
  rc=$?
  if [ "$FETCH" != "-" ]; then mkdir -p $FETCH; rsync -a -e "ssh $SSHO" ubuntu@$H:$FETCH/ $FETCH/ >> $F.progress 2>&1; fi
  echo "$(date -Is) END rc=$rc $CMD" >> $F.progress
done < $F
echo "$(date -Is) LANE DONE" >> $F.progress
