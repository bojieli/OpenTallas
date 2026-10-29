#!/bin/bash
# HEAD-START-3: rerun of the HEAD-START-2 r1 vehicle (same kit, same combo.v/tcl) + per-endpoint data-delay readout
set -euo pipefail
cd "$(dirname "$0")"
C=${1:?TT or FF}
mkdir -p out_$C && cp ../../head-start-2/ov/combo.v out_$C/combo.v && cp combo_sta.tcl out_$C/combo.tcl
docker run --rm --name "claude-head-start-3-dd-$C" --cpus=8 --memory=32g --memory-swap=32g -v /srv/opentallas-scratch2/claude/head-start-2/kit:/work:ro -v "$PWD/out_$C:/out" -e CORNER="$C" -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/run.log 2>&1"
