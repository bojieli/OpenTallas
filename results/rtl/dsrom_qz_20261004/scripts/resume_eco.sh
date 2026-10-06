#!/bin/bash
# resume a routed Z18 run from CTS with the POST_GLOBAL_ROUTE hold ECO hook (usage: resume_eco.sh SRC_RUN NEW_RUN ECO_MARGIN [SM])
# runs on ot-epyc2; source work dir read from /mnt/epyc1-scratch (EPYC1 scratch, read-only).
set -u
S=$1; R=$2; M=$3; SMV=${4:-}
T=/srv/opentallas-scratch/claude/dsrom-qtclose; WT=$T/wt-0032b7355
SRCW=/mnt/epyc1-scratch/claude/dsrom-qtclose/jobs/$S/work/orfs
J=$T/jobs/$R; W=$J/work/orfs; mkdir -p $W
rsync -a --exclude 'results/asap7/*/base/5_*' --exclude 'results/asap7/*/base/6_*' --exclude 'logs/asap7/*/base/5_*' \
  --exclude 'logs/asap7/*/base/6_*' --exclude 'reports' --exclude 'results/asap7/*/base/route.guide' $SRCW/ $W/
OLD=$(ls -d $W/results/asap7/*/base | head -1); NICK=$(basename $(dirname $OLD))
cp $WT/physical/abi3/dsrom_q_grt_hold_eco.tcl $W/hooks/post_global_route_dsrom_q_grt_hold_eco.tcl 2>/dev/null || cp /tmp/dsrom_q_grt_hold_eco.tcl $W/hooks/post_global_route_dsrom_q_grt_hold_eco.tcl
{ echo "export POST_GLOBAL_ROUTE_TCL = /work/hooks/post_global_route_dsrom_q_grt_hold_eco.tcl"; echo "export OT_ECO_HOLD_MARGIN = $M";
  [ -n "$SMV" ] && echo "export SETUP_SLACK_MARGIN = $SMV"; } >> $W/config.mk
echo "resume of $S from 4_cts with hold ECO margin $M sm ${SMV:-unchanged}; nickname $NICK" > $J/RESUME.txt
/srv/opentallas-scratch/admit.sh 34 -- docker run --rm -v $WT:/src:ro -v $W:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc \
  "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=20 do-route do-finish" > $J/launch.log 2>&1
echo $? > $J/launch.rc
tail -n 1 $J/launch.log > $J/launch.done
