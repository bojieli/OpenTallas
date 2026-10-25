#!/bin/bash
L=/srv/opentallas-scratch2/claude/s81-cores-legacy
for K in $L/*/; do K=${K%/}; N=$(basename $K); [ "$N" = _probe ] || [ "$N" = _review ] && continue
  ls $K/run/results/asap7/*/base/4_cts.odb >/dev/null 2>&1 || continue
  [ -s $L/_review/$N.ck.csv ] && grep -q pinreg $L/_review/$N.ck.csv && continue
  bash $L/_probe/review.sh $K $L/_review; echo "probed $N"
done
