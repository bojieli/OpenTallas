#!/bin/bash
# DIE-HBM-20-EPB: floorplan + place of a reshaped hfd_ep_static kit (synth reused), diagnostic probe in docker (memory cap).
#   run_place.sh KITDIR [TARGET=place]
set -uo pipefail
K=$(cd "$1" && pwd -P); IMAGE=openroad/orfs:asap7lock
touch $K/run/objects/asap7/*/base/* 2>/dev/null; find $K/run/results -name '1_*' -exec touch {} +
docker run --rm --name dh20-epb-$(basename $K) --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8'; \
  python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || echo HOLDMM_PATCH_FAIL; \
  \$M ${2:-place} > /work/run_${2:-place}.log 2>&1; rc=\$?; echo rc \$rc >> /work/run_${2:-place}.log; chown -R \$HUID:\$HGID /work; exit \$rc"
echo "rc $?" > $K/${2:-place}.rc
