#!/bin/bash
set -eu
OUT=$(mkdir -p "$1" && realpath "$1"); M=${2:-0}; R=${3:-0}; D=rtl/qwen_sys/d2d_static_20261015
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-WIDTH -I$D --top-module tb_sysface_ovl_rom -GMUT=$M -GRECOVER=$R --Mdir "$OUT/obj" \
 "$D/ot_qwen_d2d_cal_seq.sv" "$D/ot_qwen_d2d_ovl_seq.sv" "$D/qfd_d2d_cal_seq_ovl.sv" \
 physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v rtl/test/qwen_split/tb_sysface_ovl_rom.sv > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_sysface_ovl_rom" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
if [ "$M" = 0 ]; then grep -q '^SYSFACE_OVL_PASS' "$OUT/run.log"; else ! grep -q '^SYSFACE_OVL_FAIL' "$OUT/run.log"; fi
