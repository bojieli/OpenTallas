#!/bin/bash
# Qwen8K minimum parent (KIND1 / D4096 / no quant, position 8191): verilate -O1 -fno-dfg --unroll-count 4 with at most
# 3 hierarchical jobs (4 parallel child verilations peaked 450 GB), C++ -O0; then the three runs.
B=/srv/opentallas-scratch/claude/tk-hbm-harvest; D=$B/fsr; Q=$B/lorentz-margin-qwen8k; S=$Q/src; W=$Q/work
rm -rf $W; mkdir -p $W/tmp; cd $S
M=physical/hbm_die_abstracts_20261006/memory_control
P="$(sed -n '/^P="/,/"$/p' $M/run_minimum_parent_margin.sh | tr -d '\n' | sed -e 's/^P="//' -e 's/\${OT_EXTRA_G:-}//' -e 's/"$//')"
TMPDIR=$W/tmp /usr/bin/time -v -o $W/build_resources.log $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --cc --exe --build --hierarchical --timing -Wno-fatal -Werror-LATCH \
 --build-jobs 3 --verilate-jobs 1 --hierarchical-threads 1 -O1 -fno-dfg --unroll-count 4 -MAKEFLAGS OPT_SLOW=-O0 -MAKEFLAGS OPT_FAST=-O0 -MAKEFLAGS OPT_GLOBAL=-O0 \
 -CFLAGS "-DOT_KIND=1 -DOT_D=4096 -DOT_QUANT=0 -DOT_POSITION=8191" \
 --top-module tb_hbm_integrated_minimum_parent --Mdir $W/obj $P -GNORM_KIND=1 -GNORM_D=4096 -GNORM_PUBLISH_QUANT=0 $M/minimum_parent_margin.vlt -f $M/minimum_parent_margin.files.f $S/$M/hbm_integrated_minimum_parent_main.cpp > $W/build.log 2>&1
rc=$?; echo $rc > $W/build.exit
if [ $rc -eq 0 ]; then
 for mode in base wrong_release corrupt_gold; do
  R=$W/run_$mode; mkdir -p $R; cp $Q/fixture/die*_p*.hex $Q/fixture/fixture_manifest.json $R/; cd $R
  extra=""; X=$Q/fixture/gold; [ $mode = wrong_release ] && extra="+WRONG_RELEASE"; [ $mode = corrupt_gold ] && X=$Q/fixture/gold_corrupt
  timeout 8h /usr/bin/time -v -o resources.log $W/obj/Vtb_hbm_integrated_minimum_parent +DIR=$X $extra > run.log 2>&1; echo $? > run.exit
 done
fi
echo $rc > $D/qwen8k.done
