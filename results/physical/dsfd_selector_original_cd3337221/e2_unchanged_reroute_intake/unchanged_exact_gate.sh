#!/usr/bin/env bash
# Run only in clean immutable cd33372216bcd972bb9a2667d7cd69d36c0690ac source snapshot.
# Intake wrapper changes scheduling only; pinned DUT and bench unchanged.
set -eu
OUT=$1
TAG=$2
shift 2
mkdir -p "$OUT/b_$TAG"
DEFINES=()
for definition in "$@"; do DEFINES+=("+define+$definition"); done
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81ph_sel "${DEFINES[@]}" -Mdir "$OUT/b_$TAG/obj" rtl/common/ot_fwd_link_stage.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv rtl/dsrom_sys/s81_ph/dsfd_bk_selector.sv rtl/dsrom_sys/s81_ph/test/tb_s81ph_sel.sv > "$OUT/b_$TAG/build.log" 2>&1
"$OUT/b_$TAG/obj/Vtb_s81ph_sel" > "$OUT/b_$TAG/run.log" 2>&1
if grep -q '^RESULT PASS' "$OUT/b_$TAG/run.log"; then
  echo 'SELT_BENCH PASS' | tee "$OUT/b_$TAG/summary.txt"
else
  echo 'SELT_BENCH FAIL' | tee "$OUT/b_$TAG/summary.txt"
  exit 1
fi
