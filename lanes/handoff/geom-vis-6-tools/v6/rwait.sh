#!/bin/bash
# exit when an unseen render dir or a new non-HBM WAIT-VISUAL row appears (or after MAX min)
S=$1; MAX=${2:-45}; t0=$(date +%s)
while true; do
  bash $S/v2/poll2.sh $S 60 > $S/v4/poll.out 2>&1
  u=$(tail -n +2 $S/v4/poll.out)
  v=$(awk -F'\t' 'NR>1 && $5=="WAIT-VISUAL" && $1!="hbm"{print "VQ "$1" "$2" "$4" "$6}' $S/v2/vq.tsv | grep -vxFf $S/v4/vq_seen.txt)
  awk -F'\t' 'NR>1 && $5=="WAIT-VISUAL" && $1!="hbm"{print "VQ "$1" "$2" "$4" "$6}' $S/v2/vq.tsv >> $S/v4/vq_seen.txt; sort -u -o $S/v4/vq_seen.txt $S/v4/vq_seen.txt
  if [ -n "$u$v" ]; then echo "$u"; echo "$v"; exit 0; fi
  [ $(( $(date +%s) - t0 )) -gt $((MAX*60)) ] && { echo TIMEOUT; exit 0; }
  sleep 300
done
