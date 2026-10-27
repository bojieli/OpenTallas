#!/bin/bash
# run_mc.sh PKG WT NAME NSAMPLES PAR "extra args": nominal + MC for TT and FF, PAR containers at a time
PKG=$1; WT=$2; NAME=$3; N=$4; PAR=$5; shift 5
for C in TT FF; do for S in $(seq 0 $N); do echo "$C $S"; done; done | xargs -P $PAR -L1 sh -c "$PKG/run_solve.sh $PKG $WT $NAME \$0 \$1 $*"
