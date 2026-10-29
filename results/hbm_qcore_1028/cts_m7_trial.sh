#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-qcore-m7-1029
docker run --rm --name codex-qcore-m7-cts --cpus=8 --memory=32g --memory-swap=32g -v "$PWD/kit":/work -v "$PWD":/trial -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
if [ ! -f /trial/PIN_PATCH_DONE ];then
 openroad -exit /trial/pin_patch.tcl > /trial/pin_patch.log 2>&1
 grep -q PG_PIN_PATCH_PASS /trial/pin_patch.log
 mv /work/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base/3_place.odb /work/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base/3_place_legacy.odb
 mv /work/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base/3_place_pglegal.odb /work/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base/3_place.odb
 touch /trial/PIN_PATCH_DONE
fi
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl
# The documented do-cts target runs this stage only. Normal cts recurses into
# prerequisite synthesis/placement and does not preserve outer make -o flags.
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-cts
'
