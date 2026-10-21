#!/bin/bash
# QW-G5STA driver (one fleet unit per variant): setup -> pre.sh (GEN + reset_sync + strict bind) -> follow.sh (reset proj -> phase2 -> phase3 chain)
set -u
T=${1:?tag}; PM=${2:?plan}; R=/srv/opentallas-scratch/claude/mu-die-qw; S=$R/$T
bash $R/qw-g5sta-kit/setup.sh $T $PM || exit 3
bash $S/pre.sh; rc=$?; [ $rc -eq 0 ] || { echo "$(date '+%F %T %Z') QW-G5STA pre rc=$rc" >> $S/PILOT.log; exit 4; }
[ -e $S/GEN_DONE ] || exit 5
bash $S/follow.sh $T
