#!/bin/bash
set -u
SRC=/srv/opentallas-scratch2/claude/qc-mem9-rtl/kits_e9
mkdir -p ~/dq95
declare -A H=( [0]=intel2 [1]=intel2 [2]=epyc2 [3]=epyc2 [5]=epyc4 [6]=intel1 [7]=intel1 )
declare -A D=( [intel2]=/srv/opentallas-scratch2/claude/dq95 [epyc2]=/srv/opentallas-scratch3/claude/dq95 [intel1]=/srv/opentallas-scratch3/claude/dq95 [epyc4]=/srv/opentallas-scratch2/claude/dq95 )
for l in 0 1 2 3 5 6 7; do
  h=${H[$l]}; dst=${D[$h]}
  k=$(ls -d $SRC/l$l/qfd_qc_su_lane_w_l${l}_w*); kb=$(basename $k)
  if [ "$h" = intel2 ]; then mkdir -p $dst; rsync -a $k/ $dst/$kb/; else ssh -n -o ControlPath=none $h "mkdir -p $dst" && rsync -a -e "ssh -o ControlPath=none" $k/ $h:$dst/$kb/ || { echo "COPY FAIL l$l"; continue; }; fi
  echo "launch l$l $h $dst/$kb"
  setsid nohup bash -lc "ot-run --mem 48 --threads 16 --hosts $h --dir $dst/$kb --disk 40 -- bash run_kit.sh . finish 48 16" > ~/dq95/l$l.log 2>&1 < /dev/null &
  echo "pid $!"
done
