#!/bin/bash
set -euo pipefail
mkdir -p out_rowen
$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -j 8 --top-module tb_qcore_r17_rowen -Wno-fatal --Mdir out_rowen/obj -o vtb rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_qcore_r13.sv rtl/test/hbm_qcore_physical_1016/tb_qcore_r17_rowen.sv > out_rowen/build.log 2>&1
out_rowen/obj/vtb | tee out_rowen/bench.log
