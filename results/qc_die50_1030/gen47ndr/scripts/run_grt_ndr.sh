#!/bin/bash
# DIE-QC-50/gen47ndr: usage run_grt_ndr.sh CORNER  (epyc2; launched through ot-run)
set -u
C=$1; Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc-50/gen47ndr; O=$R/grt_$C; mkdir -p $O
docker run --rm --name dqc50ndr-grt-$C-$$ --memory=60g --memory-swap=60g --cpus=16 -v $Q:$Q -e OUT=$O -e CORNER=$C -e RUN=$R openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -exit $R/grt_ndr.tcl > $O/run.log 2>&1; rc=\$?; chown -R 1000:1000 $O; exit \$rc"
rc=$?; echo "rc=$rc $(date)" > $O/status; exit $rc
