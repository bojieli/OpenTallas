#!/bin/bash
# fullsys-recheck 2026-10-07 (EPYC3): DS1M minimum-parent margin build resumed from its child verilations; C++ -O0.
# step 1: child libraries only (-j 6, ~9 GB a TU); step 2: top-level verilation + compile alone; then the three runs.
B=/srv/opentallas-scratch/claude/tk-hbm-harvest; D=$B/fsr; W=$B/lorentz-margin/work
OPT="OPT_SLOW=-O0 OPT_FAST=-O0 OPT_GLOBAL=-O0"
cd $W/obj
LIBS=$(make -pn -f Vtb_hbm_integrated_minimum_parent_hier.mk 2>/dev/null | awk '/^VM_HIER_LIBS :?=/{for(i=3;i<=NF;i++) print $i}')
echo "libs: $(echo $LIBS | wc -w)" > $W/build_o0.log
TMPDIR=$W/tmp make -j 6 -f Vtb_hbm_integrated_minimum_parent_hier.mk $LIBS $OPT >> $W/build_o0.log 2>&1; rc=$?
if [ $rc -eq 0 ]; then
 TMPDIR=$W/tmp /usr/bin/time -v -o $W/build_resources_top.log make -j 6 -f Vtb_hbm_integrated_minimum_parent_hier.mk hier_build $OPT >> $W/build_o0.log 2>&1; rc=$?
fi
echo $rc > $W/build.exit
if [ $rc -eq 0 ]; then
 for mode in base wrong_release corrupt_gold; do
  R=$W/run_$mode; mkdir -p $R; cp $B/lorentz-margin/fixture/die*_p*.hex $B/lorentz-margin/fixture/fixture_manifest.json $R/; cd $R
  extra=""; X=$B/lorentz-margin/fixture/gold; [ $mode = wrong_release ] && extra="+WRONG_RELEASE"; [ $mode = corrupt_gold ] && X=$B/lorentz-margin/gold_corrupt
  timeout 8h /usr/bin/time -v -o resources.log $W/obj/Vtb_hbm_integrated_minimum_parent +DIR=$X $extra > run.log 2>&1; echo $? > run.exit
 done
fi
echo $rc > $D/ds1m.done
