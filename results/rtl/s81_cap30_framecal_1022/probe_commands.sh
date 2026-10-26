#!/bin/bash
# Run through ot-run from this evidence directory; keep all output under a new directory.
set -euo pipefail
O=${1:?new output directory}
mkdir "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 2 -Wno-fatal --top-module tb_frame_calendar probe_sources/cells.sv probe_sources/ot_s81_rly.sv probe_sources/ot_s81_land.sv tb_frame_calendar.sv --Mdir "$O/obj" -o sim > "$O/build.log" 2>&1
"$O/obj/sim" > "$O/positive.log" 2>&1
set +e
"$O/obj/sim" +MUT=1 > "$O/mutant.log" 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ] && grep -q 'FRAME_CAL FAIL real landing epoch fault' "$O/mutant.log"
