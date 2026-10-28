#!/bin/bash
# usage: run_core.sh TAG KITDIR BASE(rel to kit) ACT
O=/srv/opentallas-scratch2/claude/pg-coreconn-3/ir
docker run --rm --name pgcc3-core-$1-$$ --cpus=4 --memory=24g --memory-swap=24g -v $2:/c:ro -v $O:/o -e OT_TAG=$1 -e OT_BASE=/c/$3 -e OT_ACT=$4 \
  openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /o/core_ir.tcl" > $O/core_$1.out 2>&1
echo "DONE core $1 rc=$? $(date)" >> $O/done.txt
