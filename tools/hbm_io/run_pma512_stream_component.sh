#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mkdir -p "$out"
cd "$root"
for mut in 0 1 2; do
 verilator --binary --timing -j 1 -Wno-fatal --top-module tb_pma_stream -GMUT="$mut" --Mdir "$out/obj$mut" \
 rtl/hbm_accel/io_static_20261015/ot_hbm_pma_stream_gearbox.sv rtl/hbm_accel/io_static_20261015/tb_pma_stream.sv > "$out/build$mut.log" 2>&1
 if [[ $mut == 0 ]];then
  for phase in $(seq 0 16);do
   for ppm in -300 0 300;do
    "$out/obj0/Vtb_pma_stream" +phase="$phase" +ppm="$ppm" > "$out/phase${phase}_ppm${ppm}.log" 2>&1
    grep -q 'PASS STREAM PMA544' "$out/phase${phase}_ppm${ppm}.log"
   done
  done
  for ppm in -300 300;do
   code=0
   "$out/obj0/Vtb_pma_stream" +ppm="$ppm" +words=65536 > "$out/long_drift${ppm}.log" 2>&1 || code=$?
   [[ $code != 0 ]];grep -q 'ownership fault' "$out/long_drift${ppm}.log"
  done
 else
  code=0
  "$out/obj$mut/Vtb_pma_stream" > "$out/mutant${mut}.log" 2>&1 || code=$?
  [[ $code != 0 ]]
  if [[ $mut == 1 ]];then grep -q 'coded bit mismatch' "$out/mutant${mut}.log";else grep -q 'ownership fault' "$out/mutant${mut}.log";fi
 fi
done
printf 'PASS stream component: 51 finite4096-word phase/drift profiles, two long-drift faults, tail and early-start mutants\n'
