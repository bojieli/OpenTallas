#!/bin/bash
S=$1
while true; do
  bash $S/v2/poll2.sh $S 60 > $S/v4/poll.out 2>&1
  tail -n +2 $S/v4/poll.out | sed 's/^/UNSEEN /'
  awk -F'\t' 'NR>1 && $5=="WAIT-VISUAL" && $1!="hbm"{print "VQ "$1" "$2" "$4" "$6}' $S/v2/vq.tsv | grep -vxFf $S/v4/vq_seen.txt 2>/dev/null
  awk -F'\t' 'NR>1 && $5=="WAIT-VISUAL" && $1!="hbm"{print "VQ "$1" "$2" "$4" "$6}' $S/v2/vq.tsv >> $S/v4/vq_seen.txt
  sort -u -o $S/v4/vq_seen.txt $S/v4/vq_seen.txt
  sleep 420
done
