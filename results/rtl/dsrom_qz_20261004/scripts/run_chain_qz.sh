#!/bin/bash
# detached chain: launch (20 ORFS threads) -> launch.done -> post-CTS + post-route STA
T=/srv/opentallas-scratch/claude/dsrom-qtclose; WT=$T/wt-d9d009f4d; R=$1
mkdir -p $T/jobs/$R
$T/post_sta_qz.sh $R $WT > $T/post_$R.log 2>&1 &
OT_ORFS_NUM_CORES=${CORES:-20} WT=$WT RUN=$R STOP=finish /srv/opentallas-scratch/admit.sh 40 -- $WT/results/rtl/dsrom_qz_20261004/launch.sh
echo $? > $T/jobs/$R/launch.rc
tail -n 1 $T/jobs/$R/launch.log > $T/jobs/$R/launch.done
wait
