#!/bin/bash
# Run through ot-run. Inputs are self-contained and every attempt gets a new directory.
set -uo pipefail
D=$(cd "$1" && pwd -P); MEM=${2:-32}; CPUS=${3:-8}
. "$D/variant.env"
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
$DK run --rm --name "hbm-core-eco-$(basename "$D")-$$" --memory="${MEM}g" --memory-swap="${MEM}g" --cpus="$CPUS" \
  -v "$D":/work -e HUID=$(id -u) -e HGID=$(id -g) \
  -e OT_MAX_FANOUT -e OT_SLEW_MARGIN -e OT_SETUP_MARGIN -e OT_HOLD_MARGIN -e OT_HOLD_ALLOW_SETUP \
  -e OT_HOLD_MAXBUF -e OT_DRV_LAST -e OT_DRV_PLACE -e OT_RETIME_LAST \
  -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
    python3 /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl || exit \$?; \
    M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
    \$M do-route CORNER=TC CORNERS='tc bc' SKIP_INCREMENTAL_REPAIR=1; rc=\$?; \
    if [ \$rc = 0 ]; then \$M do-finish; rc=\$?; fi; \
    chown -R \$HUID:\$HGID /work; exit \$rc" > "$D/run_eco.log" 2>&1
rc=$?
echo "route_rc=$rc" > "$D/eco_rc.txt"
if [ "$rc" = 0 ]; then
  python3 "$D/signoff.py" run --run-dir "$D/run" --kit "$D" --corners tt,ff \
    --ff-vclk pin-flop-mean --ff-vclk-contract "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["contract"])' "$D/ECO.json")" \
    --out "$D/signoff" --docker "$DK" || rc=$?
fi
echo "final_rc=$rc" >> "$D/eco_rc.txt"
exit "$rc"
