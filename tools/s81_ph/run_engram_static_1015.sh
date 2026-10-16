#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
src=$1
out=$2
mkdir -p "$out"
p="$src/rtl/dsrom_sys/engram"
files=("$src/rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv" "$src/rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv" "$p/ot_dsrom_engram_lookup.sv" "$p/clock_partition_1015/ot_s81_engram_hash_clock_roots.sv" "$p/clock_partition_1015/ot_s81_engram_rowbank_clock_leaf.sv" "$p/static_lookup_1015/ot_s81_engram_lookup_static.sv" "$p/static_lookup_1015/tb_s81_engram_static.sv")
sha256sum "${files[@]}" > "$out/source_sha256.txt"
verilator --binary --timing -j 4 -Wno-fatal -DOT_ENGRAM_CRCMAT --top-module tb_s81_engram_static --Mdir "$out/obj" -o sim "${files[@]}" > "$out/build.log" 2>&1
"$out/obj/sim" > "$out/positive.log" 2>&1
cat "$out/positive.log"
for mut in 1 2 3 4 5 6 7; do
 set +e
 "$out/obj/sim" +MUT="$mut" > "$out/mutant_$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ];then echo "mutant survived $mut";exit 1;fi
 grep -q 'STATIC .*mismatch\|STATIC coverage missing' "$out/mutant_$mut.log"
 echo "STATIC mutant $mut rejected"
done
