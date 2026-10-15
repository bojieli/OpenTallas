#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mode=${2:-0}
mkdir -p "$out"
cd "$root"
rtl=rtl/hbm_accel/io_native_20261014
if [[ $mode == core || $mode == core-mutant ]];then
 core=$rtl/ot_hbm_kp4_correction55_static.sv
 if [[ $mode == core-mutant ]];then
  sed 's/cw\[0+:10\]\^ev\[0+:10\]/cw[0+:10]^ev[10+:10]/' "$core" > "$out/core_mutant.sv"
  core=$out/core_mutant.sv
 fi
 verilator --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_static_correction --Mdir "$out/obj" -o sim "$rtl/tb_static_correction.sv" "$core" > "$out/build.log" 2>&1
else
 sed 's/hfd_serdes487_static_window/hfd_serdes487_static_correction_window/g' rtl/hbm_accel/io_static_20261015/tb_fec_static_window.sv > "$out/tb_fec_static_window.sv"
 verilator --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-UNOPTFLAT -Irtl/dsrom_sys/s81_link --top-module tb_fec_static_window -GDMUT="$mode" --Mdir "$out/obj" -o sim "$out/tb_fec_static_window.sv" "$rtl/hfd_serdes487_static_correction_window.sv" rtl/hbm_accel/io_static_20261015/ot_hbm_static_word_cdc.sv "$rtl/ot_hbm_kp4_enc_rooted.sv" "$rtl/ot_hbm_kp4_dec_static_correction.sv" "$rtl/ot_hbm_kp4_correction55_static.sv" "$rtl/ot_hbm_kp4_chien55_map.sv" "$rtl/ot_hbm_kp4_encode52_map.sv" "$rtl/ot_hbm_kp4_syndrome55_map.sv" rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv > "$out/build.log" 2>&1
fi
code=0
"$out/obj/sim" > "$out/run.log" 2>&1 || code=$?
cat "$out/run.log"
if [[ $mode == 0 ]];then [[ $code == 0 ]];grep -q 'PASS actual FEC static-window words=2048' "$out/run.log"
elif [[ $mode == core ]];then [[ $code == 0 ]];grep -q 'PASS static correction' "$out/run.log"
elif [[ $mode == core-mutant ]];then [[ $code != 0 ]];grep -q 'static correction mismatch' "$out/run.log"
else [[ $code != 0 ]];grep -q 'FEC word error' "$out/run.log"
fi
