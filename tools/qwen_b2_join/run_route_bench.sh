#!/bin/bash
# Q-B2 10-16: build + run the route-register composed temporal bench (make_route_bench.py) for one calibration.
# usage: run_route_bench.sh OUT IMAGES CAL_DIR TB_SV [normal|mutant [EXPECT_REGEX]] [extra verilator args...]
#   CAL_DIR holds the calibrated successor sources (calibration_sources.json); TB_SV + TB_SV.defines from the generator.
set -eu
out=$1;images=$2;cal=$3;tb=$4;mode=${5:-normal};expect=${6:-}
shift 4;[ $# -gt 0 ] && shift;[ $# -gt 0 ] && shift
mkdir -p "$out"
grep -v 'tools/qwen_b2_join/tb_b2_rom_e3.sv' tools/qwen_b2_join/rom_e3_sources.f > "$out/sources.f"
ls "$cal"/*.sv >> "$out/sources.f"
echo "$tb" >> "$out/sources.f"
sha256sum $(cat "$out/sources.f") > "$out/source.sha256"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -j 8 -O1 $(cat "$tb.defines") "$@" -DOT_QFD_SEQ_SU_NOWROM -DOT_QFD_VM_NOX -DOT_QFD_VM_PARTITIONED_CLOCKS -DOT_QFDS_LU=53 -DOT_QFDS_LS=376 -Wno-fatal -Wno-TIMESCALEMOD -Irtl/hdc --top-module tb_b2_route --Mdir "$out/obj" -f "$out/sources.f" > "$out/build.log" 2>&1
if "$out/obj/Vtb_b2_route" +OT_ROM_DIR="$images/rank0/masks" +EXPECTED="$images/rank0/expected_scale_words.hex" > "$out/run.log" 2>&1;then
 test "$mode" = normal
else
 test "$mode" = mutant
 [ -z "$expect" ] || grep -q "$expect" "$out/run.log"
fi
tail -3 "$out/run.log"
