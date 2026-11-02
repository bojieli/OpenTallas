#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
trap 'chown -R "$HUID:$HGID" /work' EXIT
cd /OpenROAD-flow-scripts/flow
B=/work/run/results/asap7/kl_dsdv_bksel_q_signed_source/base
test -f "$B/1_synth.odb"
test ! -e "$B/2_floorplan.odb"
sha256sum "$B/1_synth.odb" "$B/1_synth.v" "$B/1_synth.sdc" > /work/synth_reuse_before.sha
ARGS=(DESIGN_CONFIG=/work/config.centre_PREPARED.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2)
IGNORE=(-o "$B/1_synth.odb" -o "$B/1_synth.v" -o "$B/1_synth.sdc")
# ORFS recursive dry-run cannot account for generated SDC side effects.
# Direct do-targets execute only these normal floorplan phases; no synthesis dependency traversal.
for step in do-2_1_floorplan do-2_2_floorplan_macro do-2_3_floorplan_tapcell do-2_4_floorplan_pdn do-2_floorplan; do
  make "${ARGS[@]}" "$step" >> /work/fp_make.log 2>&1
done
sha256sum -c /work/synth_reuse_before.sha > /work/synth_reuse_after.log
test -f "$B/2_floorplan.odb"
arc=0
ODB="$B/2_floorplan.odb" TARGETS=/work/allFF_target_recipe.json OUT="$B/2_floorplan_anchored.odb" openroad -python -exit /work/apply_allff_before_gpl.py > /work/anchors_native.log 2>&1 || arc=$?
ACTUAL="$B/2_floorplan.odb"
if [ -f "$B/2_floorplan_anchored.odb" ]; then ACTUAL="$B/2_floorplan_anchored.odb"; fi
ODB="$ACTUAL" openroad -python -exit /work/core_pg_probe.py > /work/core_pg_probe.log 2>&1
ODB="$ACTUAL" PINS=/work/pins.json OUT=/work/pin_audit_fp.json openroad -python -exit /work/pin_audit.py > /work/pin_audit_fp.log 2>&1
echo "FP/TAP/PG and native FF assignment terminal rc=$arc; PLACE/CTS not invoked"
exit "$arc"
