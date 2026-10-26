#!/bin/bash
# review.sh KIT OUTDIR : read-only post-CTS probes (docker, 16 GB cap) + renders
K=$1; O=$2; mkdir -p $O; P=/srv/opentallas-scratch2/claude/s81-cores-legacy/_probe
N=$(basename $K); ODB=$(ls $K/run/results/asap7/*/base/4_cts.odb | tail -1); SDC=$K/constraint.sdc
docker run --rm --name s81leg-probe-$N --memory 16g -v $K:$K -v $P:$P -v $O:$O openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
 ODB=$ODB OUT=$O/$N.placed.csv openroad -python -exit $K/dump_placed.py > $O/$N.dump.log 2>&1; \
 ODB=$ODB SDC=$SDC KIT=$K OUT=$O/$N.ck.csv openroad -exit $P/ck_probe.tcl > $O/$N.ck.log 2>&1; chown -R $(id -u):$(id -g) $O"
