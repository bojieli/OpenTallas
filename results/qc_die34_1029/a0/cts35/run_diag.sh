#!/bin/bash
# usage: run_diag.sh <kitname> <tag>; copies the kit (kit evidence untouched) and reruns make cts with the dump hook.
# helper sits in /work next to macro_cts_cluster.tcl (orfs_hold_mm.tcl finds it by the helper dir).
set -uo pipefail
R=/srv/opentallas-scratch2/claude/die-qc34-a0; src=$R/kits/$1; k=$R/diag35/$1
rm -rf $k; cp -a $src $k; cat $k/orfs_hold_mm.tcl $R/diag35/diag_append.tcl > $k/h_diag.tcl
sudo docker run --rm --name dqc35-diag-$2 --cpus=8 --memory=12g --memory-swap=12g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/h_diag.tcl > /work/orfs_hold_mm.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 cts
" > "$k/cts_diag.log" 2>&1
sudo chown -R $(id -u):$(id -g) $k
