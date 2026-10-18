#!/bin/bash
# LB2-QWEN-C 10-18: c_colW5 die-slice smoke with the level-9 idle fix (2092dfebe).  KIND = fix | mut
#   fix: the dv2f14bn cut slice with qfd_dv_redstn2.sv taken from this lane's source -> must SMOKE_RESULT PASS
#   mut: same + OT_QFD_L9_IDLE_MUT (the as-built ungated word) -> must FAIL with 'UNDECLARED o_n_dv_l9_W4'
set -u
KIND=$1; D=/srv/opentallas-scratch/claude/lb2qc-1018; F=/srv/opentallas-scratch/claude/layerbench-qwen-1018
SL=$D/slice_fix
if [ ! -f $SL/.ready ]; then
  mkdir -p $SL && cp $F/out/c_colW5/slice.json $F/out/c_colW5/qwc_slice_colW5.sv $SL/ && \
  sed "s#^/srv/opentallas-scratch/claude/qwen-split-compute/dv2f14bn/src/rtl/qwen_dv/qfd_dv_redstn2.sv\$#$D/src/rtl/qwen_dv/qfd_dv_redstn2.sv#" \
      $F/out/c_colW5/qwc_slice_colW5.f > $SL/qwc_slice_colW5.f.tmp && \
  grep -qx "$D/src/rtl/qwen_dv/qfd_dv_redstn2.sv" $SL/qwc_slice_colW5.f.tmp && mv $SL/qwc_slice_colW5.f.tmp $SL/qwc_slice_colW5.f && touch $SL/.ready || exit 7
fi
DEFS=""; [ "$KIND" = mut ] && DEFS="+define+OT_QFD_L9_IDLE_MUT"
BENCH_DEFS="$DEFS" bash $D/src/tools/qwen_layerbench/run_smoke.sh $SL $D/smoke_$KIND - 0 > $D/smoke_$KIND.out 2>&1; r=$?
echo "exit $r" >> $D/smoke_$KIND.out; cat $D/smoke_$KIND.out; exit $r
