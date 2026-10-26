#!/bin/bash
# Stage + run rtl/dsrom_sys/s81_head/test/tb_s81hd_native_l4.sv: prepared native B kit (prepare_head_native_l4.py
# output) against the UNPROFILED L4 reference family from this repo's HEAD, every ot_* identifier prefixed gold_
# (reference ROM model included; OT_S81HD_* switches renamed so the reference always stays default).
# Usage: native_l4_bench.sh KIT_DIR SK4_IMAGE_DIR OUT_DIR   (images: new_0/new_1.viamap.hex, used for both prefixes)
# Runs the positive and the two start/reset mutants (which must FAIL); heavy: launch via ot-run.
set -euo pipefail
KIT=$(readlink -f "$1"); IMG=$(readlink -f "$2"); O=$3
REPO=$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)
show() { git -C "$REPO" show "HEAD:$1"; }
mkdir -p "$O"/rtl "$O"/gold "$O"/images; O=$(readlink -f "$O")
cp "$KIT"/rtl/*.sv "$O"/rtl/                       # candidate, ROM blackbox (.v) excluded
show physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v > "$O"/rtl/ot_rom_4096x274_m8.v
show rtl/dsrom_sys/s81_head/test/tb_s81hd_native_l4.sv > "$O"/rtl/tb_s81hd_native_l4.sv
gold() { sed -E 's/\bot_/gold_ot_/g; s/\bOT_S81HD_/GOLD_OT_S81HD_/g'; }
for p in rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_fadd.sv rtl/v41rom/ot_v41_bmul2.sv rtl/v41rom/ot_dsrom_bmul3.sv \
         rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/dsrom_sys/s81_head/ot_s81hd_elem.sv; do
  show "$p" | gold > "$O"/gold/gold_"$(basename "$p")"
done
gold < "$O"/rtl/ot_rom_4096x274_m8.v > "$O"/gold/gold_ot_rom_4096x274_m8.v
for b in 0 1; do cp "$IMG"/new_$b.viamap.hex "$O"/images/new_$b.viamap.hex; cp "$IMG"/new_$b.viamap.hex "$O"/images/gold_$b.viamap.hex; done
! grep -hE '^\s*module\s+ot_' "$O"/gold/*
! grep -l 'gold_' "$O"/rtl/ot_*
( cd "$O" && sha256sum rtl/* gold/* images/* > MANIFEST.sha256 )
run() { local n=$1; shift
  verilator --binary --timing -j 8 -O1 -Wno-fatal "$@" --top-module tb_s81hd_native_l4 --Mdir "$O"/obj_$n \
    "$O"/rtl/*.sv "$O"/rtl/*.v "$O"/gold/*.sv "$O"/gold/*.v > "$O"/build_$n.log 2>&1 || return 3
  "$O"/obj_$n/Vtb_s81hd_native_l4 +OT_ROM_DIR="$O"/images > "$O"/run_$n.log 2>&1; local rc=$?; rm -rf "$O"/obj_$n; return $rc; }
run pos || { echo "POSITIVE FAIL"; exit 1; }
grep -m1 PASS "$O"/run_pos.log
for m in RST_ASYNC START_EARLY; do
  if run mut_$m +define+OT_S81HD_MUT_$m; then echo "MUTANT $m NOT CAUGHT"; exit 2; fi
  grep -q Fatal "$O"/run_mut_$m.log || { echo "MUTANT $m failed without assertion"; exit 2; }
  echo "MUTANT $m CAUGHT: $(grep -m1 -o 'Assertion failed.*' "$O"/run_mut_$m.log)"
done
