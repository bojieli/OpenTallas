#!/usr/bin/env bash
set -euo pipefail
out=$1; mut=${2:-0};mkdir -p "$out"
verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-UNOPTFLAT -Irtl/dsrom_sys/s81_link --top-module tb_hbm_serdes487 -GDMUT="$mut" --Mdir "$out/obj" -o sim \
 rtl/dsrom_sys/s81_link/{ot_s81_kp4_enc,ot_s81_kp4_dec,ot_pdie_serdes}.sv rtl/hbm_accel/io_native_20261014/{hfd_serdes487,tb_hbm_serdes487}.sv > "$out/build.log" 2>&1
"$out/obj/sim" +verilator+seed+3 > "$out/run.log" 2>&1
cat "$out/run.log"
grep -q 'HBM_SERDES487.* PASS' "$out/run.log"
