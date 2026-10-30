#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-s81types-1030/iqf_current_bind/ff_fixture
for mode in default preserve; do
 k="$r/$mode"
 docker run --rm --name "codex_iqf_ff_fixture_${mode}1030" --cpus=8 --memory=32g --memory-swap=32g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 /work/run/results/asap7/dp_iqf__t1/base/3_4_place_resized.odb' > "$k/fixture.log" 2>&1
 done
