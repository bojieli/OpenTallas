#!/bin/bash
set -u
SRC=/srv/opentallas-scratch2/claude/qc-mem9-rtl/kits_e9
declare -A H=( [0]=localhost [1]=localhost [2]=epyc2 [3]=epyc2 [6]=intel1 [7]=epyc2 )
for l in 0 1 2 3 6 7; do
  h=${H[$l]}; dst=/srv/opentallas-scratch2/claude/dq95
  k=$(ls -d $SRC/l$l/qfd_qc_su_lane_w_l${l}_w*); kb=$(basename $k)
  if [ "$h" != localhost ]; then ssh -n -o ControlPath=none $h "mkdir -p $dst" && rsync -a -e "ssh -o ControlPath=none" $k/ $h:$dst/$kb/ || { echo "COPY FAIL l$l"; continue; }; fi
  echo "launch l$l $h $dst/$kb"
  setsid nohup bash -lc "ot-run --mem 48 --threads 16 --hosts $h --dir $dst/$kb --disk 25 -- bash run_kit.sh . finish 48 16" > ~/dq95/l$l.log 2>&1 < /dev/null &
done
