#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-pc-reload-0018/finalize
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
run_native() {
  $DK run --rm --name codex-pc-fresh-finalize-0018 --cpus=8 --memory=32g --memory-swap=32g -v "$D":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || exit 9; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-route CORNER=TC "CORNERS=tc bc" SKIP_INCREMENTAL_REPAIR=1' > "$D/fresh_route.log" 2>&1
}
run_native
$DK run --rm -v "$D":/work openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /work
python3 "$D/clk_geom_diff.py" "$D/ORIGINAL.clock.tsv" "$D/reload_post_grt.clock.tsv" --json "$D/original_to_grt.clock_diff.json"
bash "$D/clk_freeze_check.sh" "$D" > "$D/clk_freeze_check.log" 2>&1
B=$D/run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base
python3 "$D/clk_geom_diff.py" "$D/ORIGINAL.clock.tsv" "$B/clk_freeze_post.tsv" --json "$D/original_to_route.clock_diff.json"
$DK run --rm --name codex-pc-fresh-finish-0018 --cpus=8 --memory=32g --memory-swap=32g -v "$D":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-finish CORNER=TC "CORNERS=tc bc"' > "$D/native_finish.log" 2>&1
$DK run --rm -v "$D":/work openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /work
bash "$D/clk_freeze_check.sh" "$D" > "$D/clk_freeze_final.log" 2>&1
python3 "$D/clk_geom_diff.py" "$D/ORIGINAL.clock.tsv" "$B/clk_freeze_post.tsv" --json "$D/original_to_final.clock_diff.json"
bash "$D/run_kit_kv.sh" "$D" post 32 8 > "$D/native_post.log" 2>&1
printf 'NATIVE_ROUTE_FINISH_POST_COMPLETE_NOT_AUTOMATICALLY_SIGNED\n' > "$D/RESULT"
