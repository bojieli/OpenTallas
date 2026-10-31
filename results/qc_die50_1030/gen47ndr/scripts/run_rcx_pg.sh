#!/bin/bash
# usage run_rcx_pg.sh RUNDIR  -> RUNDIR/clk_rcx_pg.spef
set -u
D=$1; Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc-50/gen47ndr
docker run --rm --name dqc50ndr-rcxpg-$(basename $D)-$$ --memory=60g --memory-swap=60g --cpus=8 -v $Q:$Q -e DB=$R/$D/clk_drt.odb -e OUT=$R/$D/clk_rcx_pg.spef -e RUN=$R openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 8 -exit $R/rcx_pg.tcl > $R/$D/rcx_pg.log 2>&1; rc=\$?; chown -R 1000:1000 $R/$D; exit \$rc"
