#!/bin/bash
# run_mc.sh PKG NAME NSAMPLES PAR "args" : nominal + MC for TT and FF, PAR containers at a time
PKG=$1; NAME=$2; N=$3; PAR=$4; shift 4
mkdir -p $PKG/out/$NAME
for C in TT FF; do for S in $(seq 0 $N); do echo "$C $S"; done; done | xargs -P $PAR -L1 sh -c "$PKG/run_solve.sh $PKG $NAME \$0 \$1 $*"
