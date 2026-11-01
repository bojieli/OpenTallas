#!/bin/bash
set -eu
B=/srv/opentallas-scratch2/claude/codex-parent-hold/r3
mkdir -p "$B/hold_parent/macros"
DOCKER=docker
$DOCKER info >/dev/null 2>&1 || DOCKER='sudo docker'
for n in hold_tx hold_rx; do
 K="$B/$n"
 mkdir -p "$K/views"
 cp "$B/export_views.tcl" "$K/export_views.tcl"
 $DOCKER run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc "set -eu; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for C in TT FF; do OT_CORNER=\$C TOP=$n openroad -exit /work/export_views.tcl > /work/export_\${C}.log 2>&1; done"
 python3 "$B/abstract_pin_stub.py" "$K/views/${n}_raw.lef" "$K/views/${n}_access.lef"
 cp "$K/views/${n}_access.lef" "$B/hold_parent/macros/$n.lef"
 cp "$K/views/${n}_tt.lib" "$K/views/${n}_ff.lib" "$B/hold_parent/macros/"
done
nohup "$HOME/.local/bin/ot-run" --mem 8 --threads 2 --hosts localhost --dir "$B/hold_parent" -- bash "$B/run_route.sh" "$B/hold_parent" > "$B/hold_parent/route.otrun.log" 2>&1 < /dev/null &
echo "PARENT_PID=$!"
