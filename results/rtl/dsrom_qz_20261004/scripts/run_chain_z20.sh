#!/bin/bash
# detached chain (Z20*): launch (ORFS threads) -> launch.done -> post-CTS + post-route STA.  usage: FH=<um> run_chain_z20.sh RUN
T=/srv/opentallas-scratch/claude/dsrom-qtclose; WT=$T/wt-e9b6fdd31; R=$1
mkdir -p $T/jobs/$R
$T/post_sta_qz.sh $R $WT > $T/post_$R.log 2>&1 &
D="-sink_clustering_enable -repair_clock_nets -sink_clustering_size 30 -sink_clustering_max_diameter 50 -distance_between_buffers 60 -apply_ndr full -balance_levels"
OT_ORFS_NUM_CORES=${CORES:-20} WT=$WT RUN=$R STOP=finish QX=10 HM=0.025 SM=20 CTSA="$D" FH=$FH /srv/opentallas-scratch/admit.sh 32 -- $WT/results/rtl/dsrom_qz_20261004/Z20/launch.sh
echo $? > $T/jobs/$R/launch.rc
tail -n 1 $T/jobs/$R/launch.log > $T/jobs/$R/launch.done
wait
