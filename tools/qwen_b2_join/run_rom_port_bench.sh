#!/bin/bash
set -eu
out=$1;images=$2;mode=${3:-normal}
opt="";if [ "$mode" = mutant ];then opt=-DOT_QFD_B2_PREFETCH_MUT;fi
mkdir -p "$out"
sha256sum $(cat tools/qwen_b2_join/rom_port_sources.f) > "$out/source.sha256"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -j 8 -O1 $opt -DOT_QFD_SEQ_SU_NOWROM -DOT_QFD_VM_NOX -DOT_QFDS_LU=53 -DOT_QFDS_LS=376 -Wno-fatal -Wno-TIMESCALEMOD -Irtl/hdc --top-module tb_b2_rom_port --Mdir "$out/obj" -f tools/qwen_b2_join/rom_port_sources.f > "$out/build.log" 2>&1
if "$out/obj/Vtb_b2_rom_port" +OT_ROM_DIR="$images/rank0/masks" +EXPECTED="$images/rank0/expected_scale_words.hex" > "$out/run.log" 2>&1;then
 test "$mode" = normal
else
 test "$mode" = mutant
 rg -q 'actual ROM.*hardmul mismatch' "$out/run.log"
fi
cat "$out/run.log"
