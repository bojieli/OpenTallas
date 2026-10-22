#!/bin/bash
set -euo pipefail
export VL_JOBS=8 HDC_V41_ARITH=chunk8
mkdir -p out
python3 tools/hbm_layer_vehicle/sm_mv_unit.py run --fixtures fixtures --weights weights --bundle bundle --work work --out out/positive.json --recs 4 --sm0-only > out/positive.log 2>&1
python3 tools/hbm_layer_vehicle/sm_mv_unit.py run --fixtures fixtures --weights weights --bundle bundle --work work --out out/wbit.json --recs 4 --sm0-only --mut wbit > out/wbit.log 2>&1 || test -f out/wbit.json
python3 tools/hbm_layer_vehicle/sm_mv_unit.py run --fixtures fixtures --weights weights --bundle bundle --work work --out out/nopkt.json --recs 4 --sm0-only --mut nopkt > out/nopkt.log 2>&1 || test -f out/nopkt.json
cat out/positive.json
