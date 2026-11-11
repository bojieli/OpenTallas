#!/bin/bash
# STM-DQ old-vs-new bench (DIE-QC-97 11-10).  From the repo root:
#   bash rtl/test/qwen_dv/static_stream/run_tile_stmdq.sh <out_dir> <MUT> [<old_tile.sv>] [EDGES]
# <old_tile.sv> = the unchanged qfd_dv_stream_tile.sv (default: git show 5333b7dca83:rtl/qwen_dv/qfd_dv_stream_tile.sv);
# it is renamed to qfd_dv_stream_tile_old in <out_dir>.  The new tile is built with +define+OT_QC_STMDQ.
# MUT 0 = positive (exit 0 only on "STMDQ_EQ PASS"); MUT 41 / 42 / 43 = must-fail controls (exit = simulator status,
# $fatal STMDQ_MISMATCH -> non-zero; an escaped mutant exits 0 and fails its expect=fail bench).
# VERILATOR: verilator binary (default: verilator on PATH).
set -uo pipefail
OUT=${1:?out_dir}; M=${2:?MUT}; OLD=${3:-}; EDGES=${4:-200000}
VL=${VERILATOR:-verilator}
# VL_EXTRA: extra verilator options (e.g. a fast C++ build: --output-split 3000 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0")
mkdir -p "$OUT"; $VL --version
if [ -z "$OLD" ]; then git show 5333b7dca83:rtl/qwen_dv/qfd_dv_stream_tile.sv > "$OUT/old_src.sv" || exit 2; OLD="$OUT/old_src.sv"; fi
sed 's/^module qfd_dv_stream_tile #(/module qfd_dv_stream_tile_old #(/' "$OLD" > "$OUT/qfd_dv_stream_tile_old.sv"
grep -q '^module qfd_dv_stream_tile_old #(' "$OUT/qfd_dv_stream_tile_old.sv" || { echo "RENAME_FAIL"; exit 2; }
SRC="rtl/test/qwen_dv/static_stream/tb_stream_tile_stmdq.sv $OUT/qfd_dv_stream_tile_old.sv rtl/qwen_dv/qfd_dv_stream_tile.sv"
sha256sum $SRC "$OLD"
eval $VL --binary --timing -j 8 -Wno-fatal ${VL_EXTRA:-} +define+OT_QC_STMDQ --top-module tb_stream_tile_stmdq -GMUT="$M" -GEDGES="$EDGES" \
  --Mdir "$OUT/obj" $SRC > "$OUT/build.log" 2>&1 || { echo "BUILD_FAIL MUT$M"; tail -20 "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_stream_tile_stmdq" 2>&1 | tee "$OUT/run.log"; code=${PIPESTATUS[0]}
rm -rf "$OUT/obj"
echo "MUT$M sim exit $code"
if [ "$M" = 0 ]; then grep -q 'STMDQ_EQ PASS' "$OUT/run.log" && [ "$code" -eq 0 ] && exit 0; exit 1; fi
exit "$code"
