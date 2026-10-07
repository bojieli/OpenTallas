#!/bin/bash
# Integrated minimum parent (ND2/NSM2, all exact levers) with the margin CP:
# SU_PIN_MARGIN=1 SU_RELEASE_REPLAY=1 SU_ADMIT_SHADOW=3 SU_PARALLEL_PHASE_VALIDATION=1
# SU_OWNER_VETO_POLARITY=1 (c89ee8582). Verilate (hierarchical) + C++ build + run.
# usage: run_minimum_parent_margin.sh <src_root> <work> <fixture_dir> <retained_stage_dir> <verilator>
# env: OT_EXTRA_G (extra -G overrides, e.g. Qwen8K KIND1/D4096/no quant), OT_CFLAGS (matching -DOT_* for
# the harness), OT_CORRUPT_DIR (gold dir with one corrupted golden word: negative control run).
set -u; S=$1; W=$2; FX=$3; RS=$4; V=$5; mkdir -p "$W/tmp"; cd "$S"
M=physical/hbm_die_abstracts_20261006/memory_control
P="-GENABLE=1 -GCOMBINED_ENABLE=1 -GW2_RESULT_ENABLE=1 -GW2_SECTOR_ENABLE=1 -GSU_ENABLE=1 -GSU_PROVIDER_ADAPTER=1
 -GSU_REGISTERED_OUTPUTS=1 -GSU_REGISTERED_STATUS=1 -GSU_REGISTERED_BOUNDARY=1 -GSU_BALANCED_OWNER_BOUNDARY=1
 -GSU_FOUR_COMBINATIONAL_CUTS=1 -GSU_FAST_OWNER_FRONTIER=1 -GSU_PARALLEL_PHASE_VALIDATION=1 -GSU_OWNER_VETO_POLARITY=1
 -GSU_PIN_MARGIN=1 -GSU_RELEASE_REPLAY=1 -GSU_ADMIT_SHADOW=3
 -GND=2 -GNSM=2 -GNS=2 -GNPC=2 -GMEM_WORDS=2097152 -GVM_AW=21 -GFORMATTER_ENABLE=1 -GNORMAL_GATHER_ENABLE=1
 -GLOCAL_CP_RESET_ENABLE=1 -GTW=17 -GPW=20 -GIMW=14 -GSFU_C12_ENABLE=1 -GSFU_NATIVE_VM_ENABLE=1 -GNORM_C12_ENABLE=1
 -GNORM_KIND=0 -GNORM_N=64 -GNORM_D=5120 -GNORM_RD=0 -GNORM_AW=24 -GNORM_PUBLISH_QUANT=1 -GNORM_NATIVE_VM_ENABLE=1
 -GNORM_NATIVE_INPUT_CP=1 ${OT_EXTRA_G:-}"
TMPDIR=$W/tmp /usr/bin/time -v -o $W/build_resources.log "$V" --cc --exe --build --hierarchical --timing -Wno-fatal -Werror-LATCH \
 --build-jobs ${OT_BUILD_JOBS:-2} --verilate-jobs 1 --hierarchical-threads 1 -O2 --top-module tb_hbm_integrated_minimum_parent \
 --Mdir $W/obj ${OT_CFLAGS:+-CFLAGS "$OT_CFLAGS"} $P $M/minimum_parent_margin.vlt -f $M/minimum_parent_margin.files.f $S/$M/hbm_integrated_minimum_parent_main.cpp \
 > $W/build.log 2>&1
rc=$?; echo $rc > $W/build.exit; [ $rc -eq 0 ] || exit $rc
modes="base wrong_release"; [ -n "${OT_CORRUPT_DIR:-}" ] && modes="$modes corrupt_gold"
for mode in $modes; do
 R=$W/run_$mode; mkdir -p $R; cp $FX/die*_p*.hex $FX/fixture_manifest.json $R/; cd $R
 extra=""; [ $mode = wrong_release ] && extra="+WRONG_RELEASE"
 gd=$RS; [ $mode = corrupt_gold ] && gd=$OT_CORRUPT_DIR
 /usr/bin/time -v -o resources.log $W/obj/Vtb_hbm_integrated_minimum_parent +DIR=$gd $extra > run.log 2>&1; echo $? > run.exit
done
