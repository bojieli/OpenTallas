#!/bin/bash
# usage: run.sh <src_root> <out_dir>   (ORFS asap7lock, 16 threads, route at 770 ps)
set -u; S=$1; O=$2; mkdir -p "$O"
docker run --rm --name ha2bk-$(basename "$O") -v "$S":/src:ro -v "$O":/work openroad/orfs:asap7lock bash -lc \
 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/src/physical/hbm_ha2_owner_banked_20261006/config_r2.mk WORK_HOME=/work NUM_CORES=16 finish; rc=$?; chmod -R a+rwX /work; exit $rc' > "$O/run.log" 2>&1
echo $? > "$O/terminal.exit"
