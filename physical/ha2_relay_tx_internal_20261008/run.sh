#!/bin/bash
set -eu
S=$1
O=$2
mkdir -p "$O"
set +e
docker run --rm -e HA2_FENCE_W=${HA2_FENCE_W:-100.008} -e HA2_FENCE_YM=${HA2_FENCE_YM:-10.8} -v "$S":/src:ro -v "$O":/work openroad/orfs:asap7lock bash -lc '
export HA2_TARGET="'${HA2_TARGET:-finish}'"
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
make DESIGN_CONFIG=/src/physical/ha2_relay_tx_internal_20261008/config.mk WORK_HOME=/work NUM_CORES=8 synth
printf "read_db /work/results/asap7/ha2_relay_tx_internal/base/1_synth.odb\nsource /src/physical/ha2_relay_tx_internal_20261008/inventory.tcl\n" > /work/inventory.tcl
openroad -exit /work/inventory.tcl > /work/mapped_inventory.log 2>&1
make DESIGN_CONFIG=/src/physical/ha2_relay_tx_internal_20261008/config.mk WORK_HOME=/work NUM_CORES=8 ${HA2_TARGET:-finish}
' > "$O/run.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$O/terminal.exit"
exit "$rc"
