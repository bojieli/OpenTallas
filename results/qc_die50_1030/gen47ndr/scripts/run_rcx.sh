#!/bin/bash
# DIE-QC-50/gen47ndr: usage run_rcx.sh TAG  -> RCX (rcx_TAG/clk_rcx.spef) then readout TT + FF (rd_TAG_{TT,FF}/edges_raw.txt)
set -u
T=$1; Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc-50/gen47ndr
run() { local O=$1 S=$2 C=$3; mkdir -p $O; docker run --rm --name dqc50ndr-$(basename $O)-$$ --memory=60g --memory-swap=60g --cpus=16 -v $Q:$Q -e OUT=$O -e RUN=$R -e TAG=$T -e CORNER=$C openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -exit $R/$S > $O/run.log 2>&1; rc=\$?; chown -R 1000:1000 $O; exit \$rc"; local rc=$?; echo "rc=$rc $(date)" > $O/status; return $rc; }
[ -s $R/rcx_$T/clk_rcx.spef ] || run $R/rcx_$T rcx.tcl TT || exit 1
run $R/rd_${T}_TT read_rcx.tcl TT & run $R/rd_${T}_FF read_rcx.tcl FF & wait
