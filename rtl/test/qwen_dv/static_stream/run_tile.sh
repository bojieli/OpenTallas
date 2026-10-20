#!/bin/bash
# qfd_dv_stream_tile bench (Verilator 5.050, the closure daemon's version).  From the repo root:
#   bash rtl/test/qwen_dv/static_stream/run_tile.sh <out_dir> <MUT>
# MUT 0 = positive (exit 0 only on "STREAM_TILE_EQ PASS"); MUT 2/21/22/31/32/33/34 = negative controls: the exit status is
# the simulator's ($fatal STREAM_TILE_MISMATCH -> non-zero), so an escaped mutant exits 0 and fails its expect=fail bench.
set -uo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
OUT=${1:?out_dir}; M=${2:?MUT}
mkdir -p "$OUT"; verilator --version
SRC="rtl/test/qwen_dv/static_stream/tb_stream_tile.sv rtl/qwen_dv/qfd_dv_stream.sv rtl/qwen_dv/qfd_dv_stream_tile.sv"
sha256sum $SRC
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_stream_tile -GMUT="$M" --Mdir "$OUT/obj" $SRC > "$OUT/build.log" 2>&1 \
  || { echo "BUILD_FAIL MUT$M"; tail -20 "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_stream_tile" 2>&1 | tee "$OUT/run.log"; code=${PIPESTATUS[0]}
rm -rf "$OUT/obj"
echo "MUT$M sim exit $code"
if [ "$M" = 0 ]; then grep -q 'STREAM_TILE_EQ PASS' "$OUT/run.log" && [ "$code" -eq 0 ] && exit 0; exit 1; fi
exit "$code"
