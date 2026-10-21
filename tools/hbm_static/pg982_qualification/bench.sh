#!/bin/bash
set -euo pipefail
ROOT=${PG982_RUN_ROOT:?PG982_RUN_ROOT must name the immutable staged run root}
cd "$ROOT/src"
mkdir -p "$ROOT/proof982"
bash tools/hbm_static/su_pgslice_rg_vl_run.sh "$ROOT/proof982/m0" 0 1200 1 > "$ROOT/proof982/m0.log" 2>&1
grep -q 'PGSLICE_RG PASS checks=' "$ROOT/proof982/m0/bench.log"
bash tools/hbm_static/su_pgslice_rg_vl_run.sh "$ROOT/proof982/m4" 4 300 1 > "$ROOT/proof982/m4.log" 2>&1
grep -q 'PGSLICE_RG FAIL errors=' "$ROOT/proof982/m4/bench.log"
printf '%s\n' 'PG982_EXISTING_M0_M4_EXPECTATIONS_MET'
