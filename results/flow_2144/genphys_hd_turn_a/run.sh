#!/bin/bash
set -u
V=$1
B=/srv/opentallas-scratch2/claude/codex-genphys-ab-2144
K=$B/$V
export AB_VARIANT=$V
docker run --rm --name genphys-ab-$V-2144 --cpus 8 --memory 24g --memory-swap 24g -v "$K":/work -e AB_VARIANT -e HUID=1000 -e HGID=1000 -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"
if [ "$AB_VARIANT" = baseline ]; then
 OT_VCLK_CORNER=ff $M grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=5 > /work/ab_grt.log 2>&1
else
 if grep -Eq "^export CORNERS = .*tc.*bc" /work/config.mk; then
  OT_VCLK_CORNER=ff $M grt CORNER=BC HOLD_SLACK_MARGIN=5 > /work/ab_grt.log 2>&1
 else
  OT_VCLK_CORNER=ff $M grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=5 > /work/ab_grt.log 2>&1
 fi
fi
rc=$?; echo "$rc" > /work/ab_grt.rc
if [ "$rc" = 0 ]; then
 O5=$(find /work/run/results -name 5_1_grt.odb | head -1)
 for c in TT FF; do
  OT_POSTCTS_GRT=1 OT_CORNER=$c ODB=$O5 openroad -exit /work/postcts_gate.tcl > /work/ab_sta_$c.log 2>&1
  echo "$?" > /work/ab_sta_$c.rc
  grep OT_POSTCTS_GATE /work/ab_sta_$c.log
 done
fi
chown -R "$HUID:$HGID" /work
exit "$rc"
'
