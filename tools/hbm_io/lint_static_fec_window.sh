#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mkdir -p "$out"
cd "$root"
verilator --lint-only --timing -Wno-fatal -Wno-lint -Wno-style -Wno-UNOPTFLAT -Irtl/dsrom_sys/s81_link --top-module hfd_serdes487_static_window \
 rtl/hbm_accel/io_static_20261015/hfd_serdes487_static_window.sv \
 rtl/hbm_accel/io_static_20261015/ot_hbm_static_word_cdc.sv \
 rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_enc_rooted.sv \
 rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_dec_rooted.sv \
 rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_encode52_map.sv \
 rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_syndrome55_map.sv \
 rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv > "$out/lint.log" 2>&1
printf 'PASS actual FEC and static-window composition source elaboration\n'
