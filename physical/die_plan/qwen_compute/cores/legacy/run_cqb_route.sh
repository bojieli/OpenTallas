#!/bin/bash
# Resume a reviewed, clock-balanced QC core GRT snapshot. Apply small FF hold
# repair on real GRT RC before DRT; never rerun synthesis/place or the old tree.
set -euo pipefail
K=$(cd "$1" && pwd)
C=${2:-8}
M=${3:-32}
DK=docker
docker ps >/dev/null 2>&1 || DK='sudo docker'
set +e
$DK run --rm --name "qc-cqb-$(basename "$K")-$$" --cpus="$C" --memory="${M}g" --memory-swap="${M}g" \
  -v "$K":/work -e HUID="$(id -u)" -e HGID="$(id -g)" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES='"$C"' CORNER=BC CORNERS=bc SKIP_INCREMENTAL_REPAIR=1 SKIP_ANTENNA_REPAIR=1 do-grt do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES='"$C"' do-finish do-generate_abstract
F=$(find /work/run/results/asap7 -name 6_final.odb -print -quit)
N=$(sed -n "s/^export DESIGN_NAME = //p" /work/config.mk | head -1)
for c in TT FF; do OT_CORNER=$c DESIGN_NAME=$N ODB=$F SPEF=${F%.odb}.spef openroad -exit /work/corners.tcl > /work/sta_$c.log 2>&1; done
chown -R "$HUID:$HGID" /work
' > "$K/run_cqb_route.log" 2>&1
rc=$?
set -e
printf 'route_finish_rc=%s\n' "$rc" > "$K/cqb_rc.txt"
if [ "$rc" != 0 ]; then exit "$rc"; fi
SIGNOFF_DOCKER="$DK" python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff_cqb" --image openroad/orfs:asap7lock > "$K/signoff_cqb.log" 2>&1
