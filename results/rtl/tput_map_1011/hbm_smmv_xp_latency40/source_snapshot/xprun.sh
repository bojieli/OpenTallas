#!/bin/bash
# usage: xprun.sh <outname> <MUT|-> <PROGRAM> <XQ> [extra defs] -- [plusargs]
S=/srv/opentallas-scratch/claude/smmvxp; n=$1; M=$2; P=$3; XQ=$4; shift 4
X=""; while [ $# -gt 0 ] && [ "$1" != "--" ]; do X="$X $1"; shift; done; shift || true
[ "$M" = "-" ] && M=""
DF="-DXBD +define+NCL=4 +define+WVM8 +define+XQ=$XQ +define+WIN=8 $X"
mkdir -p $S/runs/$n; cd $S/src
PROGRAM=$P J=16 DEFS="$DF" TAG=${TAG:-} bash rtl/hbm_accel/generic/adapters/tb/run_smmv_tput.sh ds $S/runs/$n "$M" +WD=200000 "$@" > $S/runs/$n.${M:-base}${TAG:+_$TAG}.out 2>&1 < /dev/null
echo "done rc=$?" >> $S/runs/$n.${M:-base}${TAG:+_$TAG}.out
