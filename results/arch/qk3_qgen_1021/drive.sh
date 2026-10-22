#!/bin/bash
# QK3-QGEN 10-21: drive_ng.sh minus setup: pre.sh (GEN + reset_sync + strict bind) -> hier check -> follow.sh
# (bind_gate DIAG_OPEN_OK -> fault census -> reset projection -> phase2 -> phase3 GRT/STA tt ff ss + die clock check)
set -u
T=${1:?tag}; R=/srv/opentallas-scratch/claude/mu-die-qw; S=$R/$T
export OT_SPLIT_FAULT_SOURCE_BITS=1 DIAG_OPEN_OK=1 ${FDEG:+FDEG=$FDEG}
bash $S/pre.sh; rc=$?; [ $rc -eq 0 ] || { echo "$(date '+%F %T %Z') QK3 pre rc=$rc" >> $S/PILOT.log; [ -e $S/FINAL_GEN_FAIL ] || echo "GEN rc=$rc" > $S/FINAL_GEN_FAIL; exit 4; }
[ -e $S/PRE_DONE ] || exit 5
bash $R/qko-qdie-kit/die_hier_check.sh $S > $S/hier_check.line 2>&1; hc=$?
echo "$(date '+%F %T %Z') QK3 hier check rc=$hc $(tail -n 1 $S/hier_check.line | cut -c1-300)" >> $S/PILOT.log
[ $hc -eq 0 ] || { echo hier > $S/FINAL_HIER_FAIL; exit 6; }
bash $S/follow.sh $T
