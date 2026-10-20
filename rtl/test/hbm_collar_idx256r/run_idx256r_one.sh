#!/bin/bash
# L2H-PAD 10-19: one IDX256R case on the fleet (Verilator 5.050 = closure daemon): run_idx256r_one.sh <out> <MUT> [FAN32=1]
# Reference = ot_hbm_static_cfg_collar_idx256 (canonical, no FAN32); DUT = ot_hbm_static_cfg_collar_idx256r.
set -euo pipefail
out=${1:?output};mut=${2:?mutant};fan=${3:-1};mkdir -p "$out";out=$(realpath "$out")
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$out/verilator.txt"
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx256r -GMUT="$mut" -GFAN32="$fan" --Mdir "$out/obj" -o tb rtl/test/hbm_collar_idx256r/tb_idx256r.sv rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar_idx256.sv rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar_idx256r.sv > "$out/build.log" 2>&1
exec "$out/obj/tb" +verilator+seed+7
