#!/bin/bash
# qwen-tp8 die lead r9: launch the die chain (real case -> PDN r5 -> full-die GRT, OT_ITERS 12, stop after GRT) on a
# fleet host through ot-run.  The case is a chain-ready die case (tools/qwen_tp8/relay_data_run.py OUT --case).
# usage: die_grt_launch.sh CASE_DIR TAG HOST [MEM_GB]     -> HOST:/srv/opentallas-scratch/claude/qwen-tp8-die/TAG/STATUS.log
set -u
C=$(readlink -f $1); T=$2; H=$3; MEM=${4:-200}
WT=$(cd $(dirname $0)/../.. && pwd)
B=/srv/opentallas-scratch/claude/qwen-tp8-die; R=$B/$T; K=$B/kit_$T
S="ssh -o ControlPath=none $H"
$S "mkdir -p $R/case_r22k $K/tools/qwen_kv_die" || exit 1
rsync -a -e 'ssh -o ControlPath=none' $C/ $H:$R/case_r22k/ || exit 1
rsync -a -e 'ssh -o ControlPath=none' $WT/tools/qwen_kv_die/chain $H:$K/tools/qwen_kv_die/ || exit 1
# DIE-FLOW 10-17: the shared die-net repeater step (OT_DIE_REPAIR=1) + its die reach table
$S "mkdir -p $K/tools/die_cluster $K/results/arch" || exit 1
rsync -a -e 'ssh -o ControlPath=none' $WT/tools/die_repeaters $WT/tools/die_reach.py $H:$K/tools/ || exit 1
rsync -a -e 'ssh -o ControlPath=none' $WT/tools/die_cluster/cluster_bounds.tcl $H:$K/tools/die_cluster/ || exit 1
git -C $WT show HEAD:results/arch/die_reach_1016.json | $S "cat > $K/results/arch/die_reach_1016.json" || exit 1
git -C $WT rev-parse --short=9 HEAD | $S "cat > $R/case_r22k/SOURCE_COMMIT"
$S "echo \"\$(date '+%F %T %Z') qwen-tp8/die chain $T queued through ot-run (--mem $MEM, OT_ITERS 12, stop after GRT)\" >> $R/STATUS.log"
exec /home/ubuntu/bin/ot-run --mem $MEM --hosts $H --dir $R -- env OT_ADMIT=pass OT_STOP=grt OT_ITERS=12 OT_ROUTE_RESET=1 OT_DIE_REPAIR=${OT_DIE_REPAIR:-0} \
  bash $K/tools/qwen_kv_die/chain/die_chain.sh r22k $R $K
