#!/bin/bash
# L2H-GEN2D-FP: cancel the OLD-floorplan GEN2d forest variants + waiting chains kx/sy (LEAD3-HBM decision step 5).
# Exact PIDs only: local wrapper (cmdline must match run_var_*.sh <tag>), its ot-run child, and the remote python on the
# variant's host (pgrep on the variant's own forest_<src>/<tag>/ path).  Logs to fp/cancel_old.log.
V=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d/forest_var; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d; LOG=$A/fp/cancel_old.log
B=/srv/opentallas-scratch/claude/hd4g/gen2d
echo "CANCEL_OLD start $(date -Is) reason: ${1:-unspecified}" >> $LOG
for T in cplanKR2 cplanKR cplanKB cplanKB3 hhKB hhR2 carrhhR carrhpR2 carrhhB cplanB hhfbK hhfbKf; do
  grep -q '^VAR_DONE' $V/$T.otrun 2>/dev/null && { echo "$T already done" >> $LOG; continue; }
  hs=$(sed -n 's/^VAR_START .* src=\([0-9a-f]*\) .*/\1/p' $V/$T.otrun | head -1); host=$(sed -n 's/^VAR_START .* host=\(\S*\) .*/\1/p' $V/$T.otrun | head -1)
  for p in $(pgrep -f "run_var_(bound|rstfb)\.sh $T "); do
    tr '\0' ' ' < /proc/$p/cmdline | grep -qE "run_var_(bound|rstfb)\.sh $T " || continue
    kids=$(pgrep -P $p); echo "$T local wrapper $p kids $kids" >> $LOG; kill $p $kids 2>>$LOG
  done
  [ -n "$hs" ] && [ -n "$host" ] && ssh -o ControlPath=none $host "pids=\$(pgrep -f '[f]orest_$hs/$T/'); echo remote \$pids; [ -n \"\$pids\" ] && kill \$pids" >> $LOG 2>&1
  echo "VAR_DONE $T CANCELLED by L2H-GEN2D-FP (old floorplan; new-floorplan forest past stream NW) $(date -Is)" >> $V/$T.otrun
done
for t in kx sy; do
  p=$(cat $A/post_carrier2_$t/chain.pid 2>/dev/null)
  [ -n "$p" ] && tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q chain_d4g2d_post_carrier2.sh && { kids=$(pgrep -P $p); echo "chain $t $p kids $kids" >> $LOG; kill $p $kids; }
done
echo "CANCEL_OLD done $(date -Is)" >> $LOG
