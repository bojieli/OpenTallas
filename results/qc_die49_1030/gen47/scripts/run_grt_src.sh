#!/bin/bash
# DIE-QC-49/gen47: usage run_grt_src.sh CORNER  (epyc2; launch through ot-run)
set -u
C=$1; V=${2:-}; Q=/srv/opentallas-scratch2/claude; S=$Q/die-qc-49/g47src; O=$S/grt_$C$V; mkdir -p $O
docker run --rm --name dqc49g47-grt-$C$V-$$ --memory=96g --memory-swap=96g --cpus=16 -v $Q:$Q -e OUT=$O -e CORNER=$C -e SRC=$S -e NDR_RC=$([ "$V" = N ] && echo 1 || echo 0) openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -exit $S/grt_src.tcl > $O/run.log 2>&1; rc=\$?; chown -R 1000:1000 $O; exit \$rc"
rc=$?; echo "rc=$rc $(date)" > $O/status; exit $rc
