#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
out="${1:-/tmp/hbm-bank-static-build}"
macro="${SRAM_MODEL:-../../../../../physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v}"
if [ -f ot_sram_1r1w_1024x256_m2_r2c2.v ]; then macro=ot_sram_1r1w_1024x256_m2_r2c2.v; fi
mkdir -p "$out"
for mut in 0 1; do
  /usr/bin/time -v -o "$out/compile-$mut.time" iverilog -g2012 -s tb_bank_static -Ptb_bank_static.MUT="$mut" -o "$out/bank-$mut.vvp" ot_vms_bank_static.sv "$macro" tb_bank_static.sv > "$out/compile-$mut.log" 2>&1
  set +e
  /usr/bin/time -v -o "$out/sim-$mut.time" vvp "$out/bank-$mut.vvp" > "$out/sim-$mut.log" 2>&1
  rc=$?
  set -e
  cat "$out/sim-$mut.log"
  if [ "$mut" -eq 0 ]; then test "$rc" -eq 0; else test "$rc" -ne 0; fi
done
printf 'PASS positive and wrong-owner mutant gate\n'
