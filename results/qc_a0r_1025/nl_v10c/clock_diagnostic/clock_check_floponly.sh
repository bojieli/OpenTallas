#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/path-qc-nl
O=/srv/opentallas-scratch2/claude/codex-qc-a0-1309
W=$R/v10c/run/nlc/work/orfs
for mode in TT FF; do
 m=pair; c=$mode; [ "$mode" != affinity ] || { m=affinity; c=FF; }
 docker run --rm --name codex-a0-floppair-1309-$mode --cpus 4 --memory 16g -v "$R/src_a":/src:ro -v "$W":/work:ro -v "$O":/own -w /own openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null; export PLIBS=\"\$(cat /work/plibs.txt)\" ODB=\$(ls /work/results/asap7/*/base/4_cts.odb | head -1) SDC=/src/physical/ref_tile/qfd_tile_nl_a0cv10/signoff.sdc PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 MODE=$m MC=$c; openroad -exit /own/clock_check_floponly.tcl" > "$O/check_floponly_$mode.log" 2>&1
 grep -E '^OT_LEAF_AFF|^A0_PAIR|^Error' "$O/check_floponly_$mode.log" || true
done
