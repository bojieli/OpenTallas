#!/bin/bash
# DIE-QC-47 BTAB PRD staged: $2 = make targets (do-grt | "do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc" | do-finish)
set -uo pipefail
D=$(cd "$1" && pwd); T=$2; TAG=$3; CPUS=${4:-8}; MEM=${5:-32}
IMAGE=openroad/orfs:asap7lock
. $D/variant.env
PATCH="python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || exit 9"
docker run --rm --name dqc47-btab-$TAG-$$ --cpus=$CPUS --memory=${MEM}g --memory-swap=${MEM}g -v "$D":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -e OT_PRD_PASS=1 -e OT_MAX_FANOUT=$OT_MAX_FANOUT -e OT_SLEW_MARGIN=$OT_SLEW_MARGIN \
  -e OT_SETUP_MARGIN=$OT_SETUP_MARGIN -e OT_HOLD_MARGIN=$OT_HOLD_MARGIN -e OT_HOLD_ALLOW_SETUP=$OT_HOLD_ALLOW_SETUP \
  -e OT_PRD_MAX_WIRE_LENGTH=0 -e OT_HOLD_MAXBUF=$OT_HOLD_MAXBUF -e OT_PAD_MASTERS= -e OT_VCLK_CORNER= \
  -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $PATCH; \
  make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS $T $ROUTE_CORNERS SKIP_INCREMENTAL_REPAIR=1; rc=\$?; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$D/run_$TAG.log" 2>&1
rc=$?; echo "RC $rc $(date)" >> $D/run_$TAG.log; exit $rc
