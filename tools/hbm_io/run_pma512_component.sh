#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mkdir -p "$out"
cd "$root"
for mut in 0 1 2; do
 verilator --binary --timing -j 1 -Wno-fatal --top-module tb_pma_544_512 -GMUT="$mut" --Mdir "$out/obj$mut" \
 rtl/hbm_accel/io_static_20261015/ot_hbm_pma_block_gearbox.sv rtl/hbm_accel/io_static_20261015/tb_pma_544_512.sv > "$out/build$mut.log" 2>&1
 code=0
 "$out/obj$mut/Vtb_pma_544_512" > "$out/run$mut.log" 2>&1 || code=$?
 cat "$out/run$mut.log"
 case "$mut" in
  0) [[ $code == 0 ]]; grep -q 'PASS PMA544->512->544 exact4096' "$out/run$mut.log";;
  1) [[ $code != 0 ]]; grep -q 'coded bit mismatch' "$out/run$mut.log";;
  2) [[ $code != 0 ]]; grep -q 'ownership fault' "$out/run$mut.log";;
 esac
done
