#!/usr/bin/env bash
set -euo pipefail
src=$1
out=$2
mkdir -p "$out"
new="$src/rtl/dsrom_sys/engram/clock_partition_1015"
files=("$src/rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv" "$src/rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv" "$src/rtl/dsrom_sys/engram/ot_dsrom_engram_lookup.sv" "$src/rtl/dsrom_sys/engram/dsfd_engram_lkp.sv" "$new/ot_s81_engram_hash_clock_roots.sv" "$new/ot_s81_engram_lookup_clock_roots.sv" "$new/dsfd_engram_lkp_clock_roots.sv" "$new/tb_s81_engram_clock_roots.sv")
sha256sum "${files[@]}" > "$out/source_sha256.txt"
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT -DOT_ENGRAM_CRCMAT --top-module tb_s81_engram_clock_roots --Mdir "$out/obj" -o sim "${files[@]}" > "$out/build.log" 2>&1
"$out/obj/sim" > "$out/positive.log" 2>&1
grep -q '^CLOCK_ROOT_EQ PASS' "$out/positive.log"
ulimit -c 0
for mutant in 1 2; do
 set +e
 "$out/obj/sim" +MUTANT="$mutant" > "$out/mutant_${mutant}.log" 2>&1
 result=$?
 set -e
 if [ "$result" -eq 0 ] || ! grep -Eq 'CLOCK_ROOT_EQ (request|beat|control|status) mismatch' "$out/mutant_${mutant}.log"; then
  echo "CLOCK_ROOT_MUTANT FAIL not killed mutant=$mutant result=$result"
  exit 1
 fi
 echo "CLOCK_ROOT_MUTANT PASS rejected mutant=$mutant result=$result"
done
cat "$out/positive.log"
