#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mut=${2:-0}
mkdir -p "$out"
cd "$root"
verilator --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-UNOPTFLAT -Irtl/dsrom_sys/s81_link --top-module tb_fec_static_window -GDMUT="$mut" --Mdir "$out/obj" -o sim \
 rtl/hbm_accel/io_static_20261015/tb_fec_static_window.sv \
 rtl/hbm_accel/io_static_20261015/hfd_serdes487_static_window.sv \
 rtl/hbm_accel/io_static_20261015/ot_hbm_static_word_cdc.sv \
 rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_enc_rooted.sv \
 rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_dec_rooted.sv \
 rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_encode52_map.sv \
 rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_syndrome55_map.sv \
 rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv > "$out/build.log" 2>&1
code=0
"$out/obj/sim" > "$out/run.log" 2>&1 || code=$?
cat "$out/run.log"
if [[ $mut == 0 ]];then
 [[ $code == 0 ]];grep -q 'PASS actual FEC static-window words=2048' "$out/run.log"
else
 [[ $code != 0 ]];grep -q 'FEC word error' "$out/run.log"
fi
