#!/bin/bash
set -euo pipefail
C=${1:?TT or FF}
R=/srv/opentallas-scratch2/claude/codex-head-start-1851
K=/srv/opentallas-scratch2/claude/die-head-33/start/clk/kit_s25/kit
O=$R/out_$C
mkdir -p "$O"
cp "$R/overlay/combo.v" "$O/combo.v"
cp "$R/overlay/combo_run.tcl" "$O/combo.tcl"
docker run --rm --name codex-head-start-1851-$C --cpus=8 --memory=32g --memory-swap=32g -v "$K:/work:ro" -v "$O:/out" -e CORNER="$C" -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/run.log 2>&1"
