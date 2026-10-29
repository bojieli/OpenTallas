#!/bin/bash
# HEAD-START-2 GRT50 + START STA vehicle (diagnostic, GEOM-55 PASS-COND 06:17)
set -euo pipefail
cd "$(dirname "$0")"
C=${1:?TT or FF}
mkdir -p out_$C && cp ov/combo.v out_$C/combo.v && cp ov/combo_sta.tcl out_$C/combo.tcl
docker run --rm --name "claude-head-start-2-$C" --cpus=8 --memory=32g --memory-swap=32g -v "$PWD/kit:/work:ro" -v "$PWD/out_$C:/out" -e CORNER="$C" -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/run.log 2>&1'
