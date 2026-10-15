#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1")
mkdir -p "$out"
mapfile -t sources < h16_loop.sources.f
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD \
 --top-module tb_hbm_p_h16_loop_static --Mdir "$out/obj" "${sources[@]}" >"$out/build.log" 2>&1
for rows in 128 640;do
 "$out/obj/Vtb_hbm_p_h16_loop_static" +CASE_DIR="$(pwd)/h16_cases/t${rows}_h16" >"$out/t${rows}_h16.log" 2>&1
 cat "$out/t${rows}_h16.log"
done
if "$out/obj/Vtb_hbm_p_h16_loop_static" +CASE_DIR="$(pwd)/h16_cases/t640_h16" +MUT_HEAD_STRIDE >"$out/mutant_head_stride.log" 2>&1;then
 echo 'FAIL actual H16 head-stride mutant passed';exit 1
fi
cat "$out/mutant_head_stride.log"
grep -Eq 'real MB|real SE|real VM phase|real producer fault' "$out/mutant_head_stride.log"
echo 'PASS one-start actual H16 programme and actual head-stride mutant'
