#!/bin/bash
set -eu
out=$1;images=$2
mkdir -p "$out"
sha256sum $(cat tools/qwen_b2_join/rom_e3_sources.f) > "$out/source.sha256"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -j 8 -O1 -DOT_QFD_SEQ_SU_NOWROM -DOT_QFD_VM_NOX -DOT_QFD_VM_PARTITIONED_CLOCKS -DOT_QFDS_LU=53 -DOT_QFDS_LS=376 -Wno-fatal -Wno-TIMESCALEMOD -Irtl/hdc --top-module tb_b2_rom_e3 --Mdir "$out/obj" -f tools/qwen_b2_join/rom_e3_sources.f > "$out/build.log" 2>&1
"$out/obj/Vtb_b2_rom_e3" +OT_ROM_DIR="$images/rank0/masks" +EXPECTED="$images/rank0/expected_scale_words.hex" > "$out/run.log" 2>&1
cat "$out/run.log"
