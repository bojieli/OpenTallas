#!/bin/bash
# poll2.sh S M : scan hosts for render dirs newer than M min; print unseen phase-1 ones; check VISUAL-QUEUE
S=$1; M=${2:-45}
for h in epyc2 epyc4 epyc7 epyc8 epyc9 intel1; do (timeout 600 ssh -o ControlPath=none -o ConnectTimeout=15 $h "bash -s $M" < $S/v2/scan_remote.sh 2>/dev/null | grep -v rxs_control | awk -v h=$h '{p=$3; sub(/\/layout_review\/.*/,"",p); st=$3; sub(/.*\/layout_review\//,"",st); sub(/\/.*/,"",st); print h":"p" "st" "$1" "$2}' > $S/v2/p_$h.txt) & done; wait
cat $S/v2/p_*.txt | sort -u > $S/v2/p_all.txt
# key = dir + stage; unseen if dir+stage not in seen2
touch $S/v2/seen2.txt
awk '{print $1" "$2}' $S/v2/p_all.txt | sort -u | grep -vxFf $S/v2/seen2.txt | grep -viE "geom-vis-|hbm|/q_|PHY_|hnx_|ot_hgi|pvm_|accel" > $S/v2/unseen.txt
timeout 60 ssh -n -o ControlPath=none intel2 'cd ~/coord && git fetch -q origin coord/state; git show origin/coord/state:lanes/VISUAL-QUEUE.tsv 2>/dev/null' > $S/v2/vq.tsv
echo "$(date +%H:%M) unseen=$(wc -l < $S/v2/unseen.txt) vq_rows=$(wc -l < $S/v2/vq.tsv)"; cat $S/v2/unseen.txt
