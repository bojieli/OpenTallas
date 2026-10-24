#!/bin/bash
# ELEM-QK 10-24: run one warm hold-ECO variant dir (made by mk_hold.sh): ORFS do-route (from the original routed DB)
# + do-finish in docker, then main's tools/die_plan/signoff.py --corners tt,ff (verdict in D/signoff/signoff.json).
#   run_hold.sh D CPUS MEM_GB          (through ot-run)
set -uo pipefail
D=$(cd "$1" && pwd); CPUS=${2:-8}; MEM=${3:-32}
. $D/variant.env
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
NAME=elemqk-hold-$(basename $(dirname $D))-$(basename $D)-$$
$DK run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$D":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -e OT_HOLD_MARGIN=$OT_HOLD_MARGIN -e OT_HOLD_ALLOW_SETUP=$OT_HOLD_ALLOW_SETUP \
  -e OT_HOLD_MAXBUF=$OT_HOLD_MAXBUF -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
  \$M do-route $ROUTE_CORNERS SKIP_INCREMENTAL_REPAIR=1; rc=\$?; \
  if [ \$rc = 0 ]; then \$M do-finish; rc=\$?; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$D/run_hold.log" 2>&1
rc=$?
$DK run --rm -v "$D":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "route_finish_rc=$rc" > $D/rc.txt
grep -h "ELEMQK_HOLD\|RSZ-00[0-9]*\|Inserted\|hold" $D/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | tail -n 8
if [ $rc = 0 ]; then
  SIGNOFF_DOCKER="$DK" python3 -I $D/so/tools/die_plan/signoff.py run --run-dir $D/run --kit $D --out $D/signoff \
    --corners tt,ff --image "$IMAGE" > $D/signoff.log 2>&1
  echo "signoff_rc=$?" >> $D/rc.txt
  grep -E '^SIGNOFF|^  - ' $D/signoff.log | head -12
fi
