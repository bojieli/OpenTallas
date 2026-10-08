#!/bin/bash
set -eu
S=$1
O=$2
mkdir -p "$O"
set +e
docker run --rm -v "$S":/src:ro -v "$O":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/src/physical/hbm_ha2_fixedpins_20261007/config.mk WORK_HOME=/work NUM_CORES=16 finish' > "$O/run.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$O/terminal.exit"
exit "$rc"
