#!/bin/bash
# QW2-NEXTGEN 10-21: drive_c3.sh of qw2-diefix-kit with setup_ng.sh (slice slot SLOT_W x SLOT_H).  Was QW-C3-DIE: drive_g5r3.sh of qw-g5r3w-kit + slice-row gap arg (usage: drive_c3.sh TAG GEOM FAULT BASE CLASSES SGAP).
# QW-G5R3 driver (one fleet unit per variant): setup -> pre.sh (GEN + reset_sync + strict bind) -> follow.sh (fault census ->
# reset projection -> phase2 -> phase3 GRT/STA TT/FF/SS + die clock check).  usage: drive_g5r3.sh TAG GEOM FAULT [BASE]
set -u
T=${1:?tag}; R=/srv/opentallas-scratch/claude/mu-die-qw; S=$R/$T
bash $R/qw2-nextgen-kit/setup_ng.sh "$@" || { mkdir -p $S; echo "setup rc=$?" > $S/SETUP_FAIL; exit 3; }
bash $S/pre.sh; rc=$?; [ $rc -eq 0 ] || { echo "$(date '+%F %T %Z') QW-G5R3 pre rc=$rc" >> $S/PILOT.log; exit 4; }
[ -e $S/GEN_DONE ] || exit 5
# LEAD-QW2 10-21 (owner): source/file completeness parse (yosys hierarchy -check over die.v + the full RTL closure of the GEN
# source) gates the chain: FAIL -> FINAL_HIER_FAIL, no physical step
bash $R/qw2-nextgen-kit/die_hier_check.sh $S > $S/hier_check.line 2>&1; hc=$?
echo "$(date '+%F %T %Z') QW2-NEXTGEN hier check rc=$hc $(tail -n 1 $S/hier_check.line | cut -c1-300)" >> $S/PILOT.log
[ $hc -eq 0 ] || { echo hier > $S/FINAL_HIER_FAIL; exit 6; }
bash $S/follow.sh $T
