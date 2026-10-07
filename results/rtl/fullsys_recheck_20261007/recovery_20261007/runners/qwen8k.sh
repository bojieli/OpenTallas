#!/bin/bash
# Qwen8K minimum parent (KIND1 / D4096 / no quant, position 8191): verilate -O1 -fno-dfg --unroll-count 4 with at most
# 3 hierarchical jobs (4 parallel child verilations peaked 450 GB), C++ -O0; then the three runs.
B=/srv/opentallas-scratch/claude/tk-hbm-harvest; D=$B/fsr; Q=$B/lorentz-margin-qwen8k; S=$Q/src; W=$Q/work
mkdir -p $W/tmp; cd $W/obj
# Resume the existing pinned hierarchy, retaining all 168 completed objects.
# The generated hierarchy retains the original KIND1/D4096/POS8191 parameters.
TMPDIR=$W/tmp /usr/bin/time -v -o $W/build_resources_resume.log make -j 2 -f Vtb_hbm_integrated_minimum_parent_hier.mk hier_build OPT_SLOW=-O0 OPT_FAST=-O0 OPT_GLOBAL=-O0 > $W/build_resume.log 2>&1
rc=$?; echo $rc > $W/build.exit
if [ $rc -eq 0 ]; then
 for mode in base wrong_release corrupt_gold; do
  R=$W/run_$mode; mkdir -p $R; cp $Q/fixture/die*_p*.hex $Q/fixture/fixture_manifest.json $R/; cd $R
  extra=""; X=$Q/fixture/gold; [ $mode = wrong_release ] && extra="+WRONG_RELEASE"; [ $mode = corrupt_gold ] && X=$Q/fixture/gold_corrupt
  /usr/bin/time -v -o resources.log $W/obj/Vtb_hbm_integrated_minimum_parent +DIR=$X $extra > run.log 2>&1; echo $? > run.exit
 done
fi
echo $rc > $D/qwen8k.done
