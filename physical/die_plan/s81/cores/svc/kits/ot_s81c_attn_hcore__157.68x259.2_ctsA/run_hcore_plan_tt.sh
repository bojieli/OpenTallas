#!/bin/bash
set -eu
K=$(cd "$(dirname "$0")" && pwd)
for P in hcore_tt_grt_native hcore_group_plan; do
 docker run --rm --name "codex-${P}-2144" --memory=12g --memory-swap=12g --cpus=8 -v "$K":/work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/$P.tcl" > "$K/${P}.log" 2>&1
 done
