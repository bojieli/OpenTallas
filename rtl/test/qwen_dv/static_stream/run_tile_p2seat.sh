#!/bin/bash
# STM P2SEAT old-vs-new bench (QC-INT-R2-HCSETUP 11-26, class C-LEG405).  From the repo root:
#   bash rtl/test/qwen_dv/static_stream/run_tile_p2seat.sh <out_dir> <MUT> <old_tile.sv> [EDGES]
# <old_tile.sv> = the tile WITHOUT the partition change (git show <parent>:rtl/qwen_dv/qfd_dv_stream_tile.sv); it is
# renamed qfd_dv_stream_tile_old.  The new tile is built with +define+OT_QC_STM_P2SEAT (and OT_QC_STMDQ, as the 9 stm types
# carry it).  MUT 0 = positive (exit 0 only on "STMDQ_EQ PASS": every output, every edge, identical to the old tile);
# MUT 35 = must-fail control: the new tile has tree 5 broken (its xm copy never updates); the old tile has no MUT, so the
# bench must report STMDQ_MISMATCH.  Unlike the old tile, the new one routes tree 5 to its own leaves, so a wrong
# leaf -> tree map shows up as a mismatch on the so_e / so_w / xt ports.
set -uo pipefail
OUT=${1:?out_dir}; M=${2:?MUT}; OLD=${3:?old tile}; EDGES=${4:-200000}
VL=${VERILATOR:-verilator}
mkdir -p "$OUT"; $VL --version
sed "s/^module qfd_dv_stream_tile #(/module qfd_dv_stream_tile_old #(/" "$OLD" > "$OUT/qfd_dv_stream_tile_old.sv"
grep -q "^module qfd_dv_stream_tile_old #(" "$OUT/qfd_dv_stream_tile_old.sv" || { echo RENAME_FAIL; exit 2; }
SRC="rtl/test/qwen_dv/static_stream/tb_stream_tile_p2seat.sv $OUT/qfd_dv_stream_tile_old.sv rtl/qwen_dv/qfd_dv_stream_tile.sv"
sha256sum $SRC
$VL --binary --timing -j 8 -Wno-fatal +define+OT_QC_STMDQ +define+OT_QC_STM_P2SEAT --top-module tb_stream_tile_p2seat -GMUT="$M" -GEDGES="$EDGES" \
  --Mdir "$OUT/obj" $SRC > "$OUT/build.log" 2>&1 || { echo "BUILD_FAIL MUT$M"; tail -20 "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_stream_tile_p2seat" 2>&1 | tee "$OUT/run.log"; code=${PIPESTATUS[0]}
rm -rf "$OUT/obj"
echo "MUT$M sim exit $code"
if [ "$M" = 0 ]; then grep -q "STMDQ_EQ PASS" "$OUT/run.log" && [ "$code" -eq 0 ] && exit 0; exit 1; fi
exit "$code"
