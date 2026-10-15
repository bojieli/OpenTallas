#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1")
mkdir -p "$out"
mapfile -t sources < producer.sources.f
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD \
 --top-module tb_hbm_p_native_producer_static --Mdir "$out/obj" "${sources[@]}" >"$out/build.log" 2>&1
for rows in 128 640;do
 for head in $(seq -w 0 15);do
  case_dir="$(pwd)/cases/t${rows}_h${head}"
  "$out/obj/Vtb_hbm_p_native_producer_static" +CASE_DIR="$case_dir" >"$out/t${rows}_h${head}.log" 2>&1
  cat "$out/t${rows}_h${head}.log"
 done
done
if "$out/obj/Vtb_hbm_p_native_producer_static" +CASE_DIR="$(pwd)/cases/t640_h00" +MUT_SOURCE >"$out/mutant_source.log" 2>&1;then
 echo 'FAIL actual producer source-index mutant passed';exit 1
fi
cat "$out/mutant_source.log"
echo 'PASS actual producer source-index mutant rejected; component rawSC boundary only'
