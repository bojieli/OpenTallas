#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1")
mkdir -p "$out"
mapfile -t sources < norm_h16.sources.f
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD \
 --top-module tb_hbm_p_norm_h16_static --Mdir "$out/obj" "${sources[@]}" >"$out/build.log" 2>&1
for rows in 128 640;do
 "$out/obj/Vtb_hbm_p_norm_h16_static" +CASE_DIR="$(pwd)/p-norm-cases/t${rows}_h16" >"$out/t${rows}_h16.log" 2>&1
 cat "$out/t${rows}_h16.log"
done
for mutant in omit_se bypass_div disable_rne;do
 if "$out/obj/Vtb_hbm_p_norm_h16_static" +CASE_DIR="$(pwd)/p-norm-cases/mutant_${mutant}" >"$out/mutant_${mutant}.log" 2>&1;then
  echo "FAIL actual normalization mutant_${mutant} passed";exit 1
 fi
 cat "$out/mutant_${mutant}.log"
 grep -Eq 'real VM phase|real producer fault' "$out/mutant_${mutant}.log"
done
echo 'PASS actual DEN/PV-DIV-RNE component positive and actual programme mutants'
