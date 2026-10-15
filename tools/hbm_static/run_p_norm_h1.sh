#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1");mkdir -p "$out"
mapfile -t sources < norm_h1.sources.f
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_hbm_p_norm_h1_static --Mdir "$out/obj" "${sources[@]}" >"$out/build.log" 2>&1
if [[ ${2:-} == --build-only ]];then exit 0;fi
for kind in canonical ties;do
 for rows in 128 640;do
  "$out/obj/Vtb_hbm_p_norm_h1_static" +CASE_DIR="$(pwd)/p-norm-h1-${kind}/t${rows}_h1" >"$out/${kind}_t${rows}.log" 2>&1
  cat "$out/${kind}_t${rows}.log"
 done
done
if "$out/obj/Vtb_hbm_p_norm_h1_static" +CASE_DIR="$(pwd)/p-norm-h1-ties/mutant_live_SC_lease" >"$out/mutant_live_SC_lease.log" 2>&1;then echo 'FAIL liveSClease mutant passed';exit 1;fi
cat "$out/mutant_live_SC_lease.log"
grep -Eq 'real VM phase|real producer fault|real SE' "$out/mutant_live_SC_lease.log"
echo 'PASS actual H1 futureE lease and rejected liveSC lease'
