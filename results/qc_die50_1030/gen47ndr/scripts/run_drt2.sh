#!/bin/bash
# DIE-QC-50/gen47ndr: usage run_drt.sh TAG ITERS THREADS MEM_GB (epyc2; launched through ot-run)
set -u
T=$1; I=$2; N=$3; M=$4; Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc-50/gen47ndr; O=$R/drt2_$T; mkdir -p $O
docker run --rm --name dqc50ndr-drt2-$T-$$ --memory=${M}g --memory-swap=${M}g --cpus=$N -v $Q:$Q -e OUT=$O -e RUN=$R -e ITERS=$I openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $N -exit $R/drt_clk2.tcl > $O/run.log 2>&1; rc=\$?; chown -R 1000:1000 $O; exit \$rc"
rc=$?; echo "rc=$rc $(date)" > $O/status; exit $rc
