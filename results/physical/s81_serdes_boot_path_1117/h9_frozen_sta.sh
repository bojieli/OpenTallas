#!/bin/bash
set -euo pipefail
L=/srv/opentallas-scratch2/claude/fable-fix-s81-serdes
P=$L/probes_codex_0417
K=$L/H7/serdes__t13/gen/serdes__t13
for c in TT FF; do
 docker run --rm --name codex-h9-frozen-$c --cpus=4 --memory=40g -v "$K:/work:ro" -v "$P:/proof:ro" -v "$P/H9_frozen:/out" -e OT_CORNER=$c -e ODB=/proof/H9_snapshot/input.odb openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /proof/h9_frozen_sta.tcl > "$P/H9_frozen/$c.log" 2>&1 &
done
wait
for c in TT FF; do grep H_WORST_DONE "$P/H9_frozen/$c.log"; done
