#!/bin/bash
# Re-run ORFS 3_3 global place on a kit copy (CLAND proof); log -> $K/proof_3_3.log
K=$1; NAME=dq66cland-$(basename $K)-$$
rm -f $K/run/logs/asap7/*/base/3_3_place_gp.log $K/run/results/asap7/*/base/3_3_place_gp.odb
docker run --rm --name $NAME --cpus=4 --memory=24g --memory-swap=24g -v $K:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 do-3_3_place_gp; rc=\$?; chown -R $(id -u):$(id -g) /work/run; exit \$rc" > $K/proof_3_3.log 2>&1
rc=$?; echo "PLACE33 $(basename $K) rc=$rc $(date)" >> $(dirname $K)/../place_status; exit $rc
