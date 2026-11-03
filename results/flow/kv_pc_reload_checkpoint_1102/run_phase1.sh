#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-pc-reload-0018/repair
. "$D/variant.env"
export OT_MAX_FANOUT OT_SLEW_MARGIN OT_SETUP_MARGIN OT_HOLD_MARGIN OT_HOLD_ALLOW_SETUP OT_HOLD_MAXBUF
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name codex-pc-repair-checkpoint-0018 --cpus=8 --memory=16g --memory-swap=16g -v "$D":/work -e OT_MAX_FANOUT -e OT_SLEW_MARGIN -e OT_SETUP_MARGIN -e OT_HOLD_MARGIN -e OT_HOLD_ALLOW_SETUP -e OT_HOLD_MAXBUF -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || exit 9; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_1_grt CORNER=TC "CORNERS=tc bc" SKIP_INCREMENTAL_REPAIR=1' > "$D/repair_phase.log" 2>&1
$DK run --rm -v "$D":/work openroad/orfs:asap7lock chown -R "$(id -u):$(id -g)" /work
[ -s "$D/repair_checkpoint.odb" ] && [ -s "$D/REPAIR_CHECKPOINT" ] || exit 10
B=$D/run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base
python3 "$D/clk_geom_diff.py" "$B/clk_freeze_pre.tsv" "$D/repair_checkpoint.clock.tsv" --json "$D/repair_checkpoint.clock_diff.json" > "$D/repair_checkpoint.clock_diff.log"
printf 'REPAIR_CHECKPOINT_READY_UNQUALIFIED_GRT\n' > "$D/RESULT"
