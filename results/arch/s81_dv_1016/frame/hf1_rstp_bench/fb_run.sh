#!/bin/bash
# HF-1: frame bench of the RSTP=1 frames (L4 successor, as bound by the die). args: MASTER SET
cd $(dirname $0)/src || exit 2
M=$1; S=$2; O=$(dirname $0)/out_${M}_${S}
SET=$S L4=1 J=16 bash tools/s81_dv/frame_bench.sh $O $M 0; rc=$?
echo "FRAME_BENCH $M $S rc=$rc"; exit $rc
