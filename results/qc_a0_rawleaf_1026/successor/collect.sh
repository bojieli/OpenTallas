#!/bin/bash
set -euo pipefail
K=$(pwd)
test -f "$K/run/results/asap7/lsl_rawfault_m3/base/3_place.odb"
docker run --rm --cpus=4 --memory=12g --memory-swap=12g -v "$K":/work -v "$K":/out -e ODB=/work/run/results/asap7/lsl_rawfault_m3/base/3_place.odb -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/face_guard_core.py /work/run/results/asap7/lsl_rawfault_m3/base/1_2_yosys.v ot_qwen_tile_lsl_rawfault_m3 "^(clk|rst_n)$" /work/pins.json /work/face_guard_core.json
openroad -exit /work/dump.tcl > /work/ffpg.log 2>&1
openroad -exit /work/hops.tcl > /work/hops.log 2>&1
'
