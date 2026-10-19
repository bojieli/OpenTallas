#!/bin/bash
# QW-DIECLK 10-19: die-clock-only trial, regional topology (landed-regions standard), on a COPY of the dv2f18dh2
# PDN floorplan (case/floorplan_pdn.odb). Tools = claude/qw-dieclk-1019 bbe250fb5 overlaid on the dh2 dieclk tools.
#  rA = local region trees + ONE forwarded unpadded spine (balance false)   rB = same region trees on ideal entries (control)
R=/srv/opentallas-scratch/claude/qw-dieclk-1019; D=$R/d; T=$D/tools/die_clock/qwen_compute_dieclk.sh
echo "$(date '+%F %T') start" >> $R/run.log
DC_FLOORPLAN=floorplan_pdn.odb DC_MEM=64 bash $T prep $D $R/case $R/libs >> $R/run.log 2>&1 || { echo PREP_FAIL >> $R/run.log; exit 3; }
DC_MEM=85 bash $T regional $D rA >> $R/rA.log 2>&1 & pa=$!
DC_MEM=85 DC_REGIONAL_IDEAL=1 bash $T regional $D rB >> $R/rB.log 2>&1 & pb=$!
wait $pa; ra=$?; wait $pb; rb=$?
echo "$(date '+%F %T') done rA=$ra rB=$rb" >> $R/run.log
[ $ra = 0 ] && [ $rb = 0 ]
