#!/bin/bash
set -euo pipefail
trap 'chown -R "$HUID:$HGID" /work' EXIT
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
B=/work/run/results/asap7/kl_dsdv_bksel_q_signed_source/base
test -f "$B/2_floorplan.odb"
test ! -e "$B/3_place.odb"
sha256sum "$B/1_synth.odb" "$B/1_synth.v" "$B/1_synth.sdc" "$B/2_floorplan.odb" > /work/protected_cache_before.sha
ARGS=(DESIGN_CONFIG=/work/config.place_ONLY.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2)
IGNORE=()
for f in "$B"/1_* "$B"/2_*; do test ! -f "$f" || IGNORE+=(-o "$f"); done
make "${ARGS[@]}" "${IGNORE[@]}" place > /work/place.log 2>&1
sha256sum -c /work/protected_cache_before.sha > /work/protected_cache_after.log
test -f "$B/3_place.odb"
arc=0
ODB="$B/3_place.odb" openroad -python -exit /work/collect_place.py > /work/collect_place.log 2>&1 || arc=$?
ODB="$B/3_place.odb" openroad -python -exit /work/core_pg_probe.py > /work/core_pg_probe_place.log 2>&1
ODB="$B/3_place.odb" PINS=/work/pins.json OUT=/work/pin_audit_place.json openroad -python -exit /work/pin_audit.py > /work/pin_audit_place.log 2>&1
echo "COMB PLACE terminal rc=$arc; no CTS/GRT/route invoked"
exit "$arc"
