#!/bin/bash
# DIE-HBM-20-EPA: synth + floorplan + place of one probe kit in the pinned ORFS image (diagnostic probe, docker mem cap)
K=$(cd "$1" && pwd -P); N=dh20-epa-$(basename $K)
docker run --rm --name $N --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) \
  -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place > /work/probe_place.log 2>&1; rc=\$?; \
  echo \$rc > /work/probe_place.rc; chown -R \$HUID:\$HGID /work; exit \$rc"
