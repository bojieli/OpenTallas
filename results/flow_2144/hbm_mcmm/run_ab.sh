#!/bin/bash
set -euo pipefail
K=$(cd "$1" && pwd)
MODE=$2
# All mutation is confined to these new diagnostic copies.
python3 - "$K" <<'PY'
from pathlib import Path
import sys
k=Path(sys.argv[1])
assert k.parent.name=='codex-hbm-mcmm-2144' and k.name in ('ff','mcmm')
for folder in ('results','logs','reports'):
 for p in (k/'run'/folder).glob('asap7/*/base/5*'):
  if p.is_file():p.unlink()
for p in (k/'run/results').glob('asap7/*/base/route.guide'):
 p.unlink()
PY
docker run --rm --name "hbm-mcmm-$MODE-$$" --cpus 4 --memory 16g --memory-swap 16g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -e MODE="$MODE" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4"
GC="CORNER=BC CORNERS=bc"
[ "$MODE" = mcmm ] && GC=""
$M -n grt $GC > /work/plan_grt.txt 2>&1
if grep -qE "do-(1|2|3|4)[_a-z0-9-]*" /work/plan_grt.txt; then echo "NOT RUN prerequisite rebuild would invalidate A/B"; chown -R "$HUID:$HGID" /work; exit 90; fi
OT_VCLK_CORNER=ff $M grt $GC HOLD_SLACK_MARGIN=5 > /work/grt_ab.log 2>&1
rc=$?
if [ $rc = 0 ]; then
 O5=$(find /work/run/results/asap7 -name 5_1_grt.odb | head -1)
 for c in TT FF; do OT_POSTCTS_GRT=1 OT_CORNER=$c ODB=$O5 openroad -exit /work/postcts_gate.tcl > /work/ab_gate_$c.log 2>&1; done
fi
chown -R "$HUID:$HGID" /work
exit $rc
'
