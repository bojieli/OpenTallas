#!/bin/bash
# usage run_win.sh TAG SPARSE "x0 y0 x1 y1"(dbu) THREADS MEM
set -u
T=$1; S=$2; W=$3; N=$4; M=$5; Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc-50/gen47ndr; O=$R/win_$T; mkdir -p $O
docker run --rm --name dqc50ndr-win-$T-$$ --memory=${M}g --memory-swap=${M}g --cpus=$N -v $Q:$Q -e OUT=$O -e SPARSE=$S -e WIN="$W" openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $N -exit $R/mkwin.tcl > $O/run.log 2>&1; rc=\$?; chown -R 1000:1000 $O; exit \$rc"
rc=$?; echo "rc=$rc $(date)" > $O/status; exit $rc
