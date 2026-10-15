#!/usr/bin/env bash
set -euo pipefail
out=$1;emut=${2:-0};dmut=${3:-0};mkdir -p "$out"
python3 tools/s81_link/rs544.py vectors "$out/vec.hex" --n 16 --seed 5
verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-UNOPTFLAT -Irtl/dsrom_sys/s81_link --top-module tb_hbm_kp4_linear_eq -GEMUT="$emut" -GDMUT="$dmut" --Mdir "$out/obj" -o sim \
 rtl/dsrom_sys/s81_link/{ot_s81_kp4_enc,ot_s81_kp4_dec}.sv \
 rtl/hbm_accel/io_native_20261014/{ot_hbm_kp4_enc_linear,ot_hbm_kp4_dec_linear,ot_hbm_kp4_encode52_map,ot_hbm_kp4_syndrome55_map,tb_hbm_kp4_linear_eq}.sv > "$out/build.log" 2>&1
set +e
"$out/obj/sim" +vec="$out/vec.hex" +verilator+seed+11 > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
if [[ "$rc" != 0 ]];then exit "$rc";fi
grep -q '^HBM_KP4_LINEAR_EQ_PASS' "$out/run.log"
