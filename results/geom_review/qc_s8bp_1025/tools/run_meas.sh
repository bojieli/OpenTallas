#!/bin/bash
# run_meas.sh SRC NICK SRAM OUT  -- TT and FF in parallel, docker memory cap (diagnostic probe)
set -u
SRC=$1; NICK=$2; SRAM=$3; OUT=$4; mkdir -p $OUT; cp $(dirname $0)/meas.tcl $OUT/
for c in tt ff; do
 docker run --rm --name s8bp-meas-$(basename $OUT)-$c --memory=12g --memory-swap=12g --cpus=2 -v $SRC:/src:ro -v $OUT:/out \
  -e OT_CORNER=$c -e SRC=/src -e NICK=$NICK -e SRAM=$SRAM -e OUT=/out openroad/orfs:asap7lock \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/meas.tcl > $OUT/meas_$c.log 2>&1 &
done
wait; echo done $(date)
