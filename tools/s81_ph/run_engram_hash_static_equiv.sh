#!/usr/bin/env bash
# ot_s81_engram_hash_static == ot_hdc_engram_hash_shipped (rows + residues, 200k cycles); $3 = optional MUT
set -euo pipefail
ulimit -c 0
src=$1; out=$2; mkdir -p "$out"
files=("$src/rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv" "$src/rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv" "$src/rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_static.sv" "$src/rtl/dsrom_sys/engram/static_lookup_1015/tb_s81_engram_hash_static_equiv.sv")
sha256sum "${files[@]}" > "$out/source_sha256.txt"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_s81_engram_hash_static_equiv --Mdir "$out/obj" -o sim "${files[@]}" > "$out/build.log" 2>&1
if [ -n "${3:-}" ]; then "$out/obj/sim" +MUT="$3"; else "$out/obj/sim"; fi
