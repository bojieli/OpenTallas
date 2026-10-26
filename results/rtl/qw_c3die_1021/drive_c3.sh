#!/bin/bash
# QW-C3-DIE 10-21: drive_g5r3.sh of qw-g5r3w-kit + slice-row gap arg (usage: drive_c3.sh TAG GEOM FAULT BASE CLASSES SGAP).
# QW-G5R3 driver (one fleet unit per variant): setup -> pre.sh (GEN + reset_sync + strict bind) -> follow.sh (fault census ->
# reset projection -> phase2 -> phase3 GRT/STA TT/FF/SS + die clock check).  usage: drive_g5r3.sh TAG GEOM FAULT [BASE]
set -u
T=${1:?tag}; R=/srv/opentallas-scratch/claude/mu-die-qw; S=$R/$T
bash $R/qw-c3die-kit/setup_c3.sh "$@" || { mkdir -p $S; echo "setup rc=$?" > $S/SETUP_FAIL; exit 3; }
bash $S/pre.sh; rc=$?; [ $rc -eq 0 ] || { echo "$(date '+%F %T %Z') QW-G5R3 pre rc=$rc" >> $S/PILOT.log; exit 4; }
[ -e $S/GEN_DONE ] || exit 5
bash $S/follow.sh $T
