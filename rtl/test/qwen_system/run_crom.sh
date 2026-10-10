#!/usr/bin/env bash
# Exact bench of ot_qfd_crom (stream qwen-system): the DUT and the mutant (MUT = 1 must mismatch).
# usage: run_crom.sh <repo> <build dir of tools/qwen_system/crom_image.py build> <work dir>
set -euo pipefail
repo=$1; img=$2; wd=$3
mkdir -p "$wd"
src=("$repo/rtl/qwen_sys/system_20261008/ot_qfd_crom.sv" "$repo/rtl/hdc/ot_hdc_delay.sv"
     "$repo/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v"
     "$repo/rtl/test/qwen_system/tb_qfd_crom.sv")
for mut in 0 1; do
  od="$wd/obj_m$mut"
  verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-DECLFILENAME -Wno-INITIALDLY \
    -DMUT=$mut --top-module tb_qfd_crom -Mdir "$od" "${src[@]}" > "$wd/build_m$mut.log" 2>&1
  "$od/Vtb_qfd_crom" +VEC="$img/crom_vectors.hex" +OT_ROM_DIR="$img/viamap" > "$wd/run_m$mut.log" 2>&1 || true
  grep CROM_RESULT "$wd/run_m$mut.log"
done
r0=$(grep -c 'CROM_RESULT pass=1 .* mismatches=0 .* mut=0' "$wd/run_m0.log" || true)
r1=$(grep -E 'CROM_RESULT .* mismatches=[1-9][0-9]* .* mut=1' "$wd/run_m1.log" | wc -l)
if [ "$r0" = 1 ] && [ "$r1" = 1 ]; then echo "CROM_BENCH PASS (exact + mutant detected)"; else echo "CROM_BENCH FAIL"; exit 1; fi
