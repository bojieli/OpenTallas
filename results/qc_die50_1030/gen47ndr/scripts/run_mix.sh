#!/bin/bash
# usage run_mix.sh TAG CORNER SPEF1,SPEF2  -> mix_TAG_CORNER/edges_raw.txt
set -u
T=$1; C=$2; S=$3; Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc-50/gen47ndr; O=$R/mix_${T}_$C; mkdir -p $O
docker run --rm --name dqc50ndr-mix-$T-$C-$$ --memory=60g --memory-swap=60g --cpus=16 -v $Q:$Q -e OUT=$O -e CORNER=$C -e RUN=$R -e SPEFS=$S openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -exit $R/read_mix.tcl > $O/run.log 2>&1; rc=\$?; chown -R 1000:1000 $O; exit \$rc"
rc=$?; echo "rc=$rc $(date)" > $O/status; exit $rc
