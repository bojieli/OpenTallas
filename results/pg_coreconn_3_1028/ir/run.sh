#!/bin/bash
# usage: run.sh TAG KITDIR ODB SDC DENS ACT
O=/srv/opentallas-scratch2/claude/pg-coreconn-3/ir
docker run --rm --name pgcc3-ir-$1-$$ --cpus=8 --memory=48g --memory-swap=48g -v $2:/k:ro -v $O:/o -e OT_TAG=$1 -e OT_ODB=$3 -e OT_SDC=$4 -e OT_DENS=$5 -e OT_ACT=$6 \
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -exit /o/ir_tile.tcl" > $O/$1.out 2>&1
echo "DONE $1 rc=$? $(date)" >> $O/done.txt
