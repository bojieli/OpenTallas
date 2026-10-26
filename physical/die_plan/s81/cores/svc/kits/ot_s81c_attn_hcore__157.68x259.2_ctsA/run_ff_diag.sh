#!/bin/bash
set -eu
K=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name codex-hcore-cap24-ffdiag-2144 --memory=12g --memory-swap=12g --cpus=8 -v "$K":/work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/hcore_ff_grt.tcl" > "$K/cap24_ff_diag.log" 2>&1
