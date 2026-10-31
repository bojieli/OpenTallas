#!/bin/bash
# usage run_reg.sh G ITERS THREADS MEM   (partial DRT + RCX of the clock nets inside boxes_G.txt)
set -u
G=$1; I=$2; N=$3; M=$4; Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc-50/gen47ndr; O=$R/path_$G; mkdir -p $O
docker run --rm --name dqc50ndr-path-$G-$$ --memory=${M}g --memory-swap=${M}g --cpus=$N -v $Q:$Q -e OUT=$O -e RUN=$R -e ITERS=$I -e BOXES=$R/boxes_$G.txt openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $N -exit $R/drt_path.tcl > $O/run.log 2>&1; rc=\$?; chown -R 1000:1000 $O; exit \$rc"
rc=$?; echo "rc=$rc $(date)" > $O/status; exit $rc
