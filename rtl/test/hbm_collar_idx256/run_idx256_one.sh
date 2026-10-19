#!/bin/bash
set -euo pipefail
out=${1:?output};mut=${2:?mutant};fan=${3:-1};mkdir -p "$out";out=$(realpath "$out")
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx256 -GMUT="$mut" -GFAN32="$fan" --Mdir "$out/obj" -o tb rtl/test/hbm_collar_idx256/tb_idx256.sv rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar.sv rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar_idx256.sv > "$out/build.log" 2>&1
exec "$out/obj/tb"
