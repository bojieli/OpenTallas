#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-colle-exact-hold-1106
for side in ${COLLE_SIDES:-e w}; do
 k="$r/$side/repair1"; src="$r/$side/kit"
 base=$(find "$src/run/results/asap7" -mindepth 2 -maxdepth 2 -type d -name base)
 out=$(find "$k/run/results/asap7" -mindepth 2 -maxdepth 2 -type d -name base)
 docker run --rm --name "codex-colle-$side-exact4-grt" --cpus=4 --memory=24g --memory-swap=24g -v "$k":/work -v "$base":/base:ro -v "$src/signoff/ff/sdcdir":/sdc:ro -v "$out":/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/exact_four.tcl' > "$k/exact_four_grt.log" 2>&1
 docker run --rm --name "codex-colle-$side-exact4-drt" --cpus=4 --memory=24g --memory-swap=24g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 do-5_2_route do-5_3_fillcell' > "$k/exact_four_drt.log" 2>&1
 cp "$out/5_3_fillcell.odb" "$out/5_route.odb"
 cp "$out/5_1_grt.sdc" "$out/5_route.sdc"
 docker run --rm --name "codex-colle-$side-exact4-final" --cpus=4 --memory=24g --memory-swap=24g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 do-finish' > "$k/exact_four_finish.log" 2>&1
 docker run --rm -v "$k":/work openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /work
 bash "$k/clk_freeze_check.sh" "$k" > "$k/exact_four_clock_check.log" 2>&1
 done
