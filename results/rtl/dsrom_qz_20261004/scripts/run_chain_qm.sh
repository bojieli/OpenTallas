#!/bin/bash
# detached Z23 chain: admission -> Z23_launch.sh -> launch.done; post_sta_qm.sh in parallel.
# usage: JROOT=<scratch root> WT=<pinned worktree> [PD= CTSX= SM= HM= CORES= PER=] run_chain_qm.sh RUN
R=$1; T=${JROOT:?}; WT=${WT:?}
mkdir -p $T/jobs/$R
$WT/results/rtl/dsrom_qz_20261004/scripts/post_sta_qm.sh $R $WT $T > $T/post_$R.log 2>&1 &
D="-sink_clustering_enable -repair_clock_nets -sink_clustering_size 40 -sink_clustering_max_diameter 60 -distance_between_buffers 80 -balance_levels"
OT_ORFS_NUM_CORES=${CORES:-16} WT=$WT RUN=$R STOP=finish QX=10 PQ=1 QW=0 QM=${QM:-1} HM=${HM:-0.025} SM=${SM:-20} CTSA="${CTSX:-$D}" FH=192.24 PD=${PD:-0.6} PER=${PER:-0.770} JROOT=$T \
  /srv/opentallas-scratch/admit.sh ${PEAK:-32} -- $WT/results/rtl/dsrom_qz_20261004/Z23_launch.sh
echo $? > $T/jobs/$R/launch.rc
tail -n 1 $T/jobs/$R/launch.log > $T/jobs/$R/launch.done
wait
