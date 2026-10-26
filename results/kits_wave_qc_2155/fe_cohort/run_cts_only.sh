#!/bin/bash
# Checkpoint-only prototype. Invoke through ot-run; no synthesis/place/route targets.
set -euo pipefail
K=$(cd "${1:?kit directory}" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
python3 "$HERE/guard.py" "$K"
NAME=qc-fe-cts-checkpoint-$$
docker run --rm -i --name "$NAME" --cpus=8 --memory=24g --memory-swap=24g \
 -v "$K":/work -e HUID="$(id -u)" -e HGID="$(id -g)" \
 -w /OpenROAD-flow-scripts/flow "${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}" bash -s <<'INNER'
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
M=(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8)
# do-step targets have no file prerequisites; do-copy only copies this stage's ODB.
"${M[@]}" do-4_1_cts SKIP_CTS_REPAIR_TIMING=1
"${M[@]}" do-4_cts
C=/work/run/results/asap7/dp_sle_fe_v1/base/4_cts.odb
S=/work/run/results/asap7/dp_sle_fe_v1/base/4_cts.sdc
test -s "$C"; test -s "$S"
export PLIBS="$("${M[@]}" print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')"
export ODB="$C" SDC="$S" PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7
export OT_VCLK_TT="$(sed -n 's/^export OT_VCLK_TT = //p' /work/config.mk)"
export OT_VCLK_FF="$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk)"
export OT_HOLD_IN_MIN="$(sed -n 's/^export OT_HOLD_IN_MIN = //p' /work/config.mk)"
export OT_HOLD_OUT_MIN="$(sed -n 's/^export OT_HOLD_OUT_MIN = //p' /work/config.mk)"
export LAYER_PARASITICS_FILE="$(sed -n 's/^export LAYER_PARASITICS_FILE = //p' /work/config.mk)"
openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1
# Post-CTS clock/load/geometry review is mandatory; no further phase is invoked.
INNER
