#!/bin/bash
# TLOAD-ROMSTAGE old-vs-new bench (DIE-QC-97 11-11).  From the repo root:
#   bash rtl/test/qwen_dv/tload_romstage/run_tload_romstage.sh <out_dir> <MUT> [EDGES]
# Old = qfd_dv_slice_tload defaults (the flattened kit form, CAPTURE_STAGE 0 / LOCAL_JOIN 0); new = the OT_QC_TLCAP
# profile (CAPTURE_STAGE 1 / LOCAL_JOIN 1).  MUT 0 = positive (exit 0 only on "TLOAD_ROMSTAGE_EQ PASS");
# MUT 1 / 2 / 9 = must-fail controls (exit = simulator status: $fatal TLOAD_ROMSTAGE MISMATCH -> non-zero).
# VERILATOR: verilator binary (default: verilator on PATH).
set -uo pipefail
OUT=${1:?out_dir}; M=${2:?MUT}; EDGES=${3:-200000}
VL=${VERILATOR:-verilator}
mkdir -p "$OUT"; $VL --version
SRC="rtl/test/qwen_dv/tload_romstage/tb_tload_romstage.sv rtl/qwen_dv/qfd_dv_slice_tload.sv rtl/qwen_dv/qfd_dv_table_rom_loader.sv"
sha256sum $SRC
$VL --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 \
  --top-module tb_tload_romstage -GMUT="$M" -GEDGES="$EDGES" --Mdir "$OUT/obj" $SRC > "$OUT/build.log" 2>&1 \
  || { echo "BUILD_FAIL MUT$M"; tail -20 "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_tload_romstage" 2>&1 | tee "$OUT/run.log"; code=${PIPESTATUS[0]}
rm -rf "$OUT/obj"
echo "MUT$M sim exit $code"
if [ "$M" = 0 ]; then grep -q 'TLOAD_ROMSTAGE_EQ PASS' "$OUT/run.log" && [ "$code" -eq 0 ] && exit 0; exit 1; fi
exit "$code"
