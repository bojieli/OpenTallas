#!/bin/bash
# KV-CORES 10-24: run one ECO dir (mk_eco.sh): ORFS do-route from the core's routed DB with the eco_route.tcl hook, then
# do-finish (GOAL finish) or nothing more (GOAL route: SRAM cores, no GDS), then run_kit_kv.sh post = generate_abstract,
# pin audit, TT/FF corner STA + ETM views, signoff.py (KIT/signoff/signoff.json; SIGNED = closed).
#   run_eco.sh D [CPUS=8] [MEM_GB=32]           (through ot-run --mem MEM_GB --dir D)
set -uo pipefail
D=$(cd "$1" && pwd); CPUS=${2:-8}; MEM=${3:-32}
. $D/variant.env
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
NAME=kvcores-eco-$(basename $(dirname $D) | cut -c1-40)-$(basename $D)-$$
$DK run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$D":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -e OT_MAX_FANOUT=$OT_MAX_FANOUT -e OT_SLEW_MARGIN=$OT_SLEW_MARGIN \
  -e OT_SETUP_MARGIN=$OT_SETUP_MARGIN -e OT_HOLD_MARGIN=$OT_HOLD_MARGIN -e OT_HOLD_ALLOW_SETUP=$OT_HOLD_ALLOW_SETUP \
  -e OT_HOLD_MAXBUF=$OT_HOLD_MAXBUF -e OT_DRV_LAST=${OT_DRV_LAST:-0} -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
  \$M do-route $ROUTE_CORNERS SKIP_INCREMENTAL_REPAIR=1; rc=\$?; \
  if [ \$rc = 0 ]; then \$M do-finish; rc=\$?; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$D/run_eco.log" 2>&1
rc=$?
$DK run --rm -v "$D":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "route_finish_rc=$rc" > $D/rc.txt
grep -h "KVCORES_ECO\|RSZ-00[0-9]*\|Inserted" $D/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | tail -n 12
if [ $rc = 0 ]; then
  bash $D/run_kit_kv.sh $D post $MEM $CPUS; rc=$?
  echo "post_rc=$rc" >> $D/rc.txt
fi
exit $rc
