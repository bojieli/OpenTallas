#!/bin/bash
# Run remotely through that host's admission guard. Never replace old evidence.
set -euo pipefail
SRC=$1; OUT=$2; MODE=${3:-fullrank}
test ! -e "$OUT" || { echo "Refuse existing evidence directory: $OUT" >&2; exit 2; }
mkdir -p "$OUT"
S=$SRC/rtl/dsrom_sys/s81_ph
case "$MODE" in
 search)
  TOP=tb_s81ph_sel_search_pipe
  FILES=("$SRC/rtl/hdc/ot_hdc_prefix.sv" "$S/selector_native/ot_s81ph_native_sel_lib.sv"
         "$S/ot_s81ph_sel_pipeline.sv" "$S/test/$TOP.sv")
  ;;
 fullrank)
  TOP=tb_s81ph_sel
  FILES=("$SRC/rtl/hdc/ot_hdc_prefix.sv" "$SRC/rtl/common/ot_fwd_link_stage.sv"
         "$SRC/rtl/hdc/v41x/ot_hdc_v41x_sel.sv" "$SRC/rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv"
         "$SRC/rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv"
         "$SRC/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
         "$S"/ot_s81ph_*.sv "$S/dsfd_bk_selector.sv" "$S"/selector_native/*.sv "$S/test/$TOP.sv")
  ;;
 *) echo "Unknown component $MODE" >&2; exit 2;;
esac
sha256sum "${FILES[@]}" > "$OUT/sources.sha256"
verilator --binary --timing -Wno-fatal -Wno-WIDTH --top-module "$TOP" --Mdir "$OUT/build" -o tb \
  "${FILES[@]}" > "$OUT/build.log" 2>&1
if [ "$MODE" = search ]; then
 "$OUT/build/tb" > "$OUT/search.log" 2>&1
 cat "$OUT/search.log"
else
 # Full TP4 rank, 262144 scores. Spread, all-tie quota, overflow/replay.
 for family in 4 5 3; do
  "$OUT/build/tb" +full_rank_1m +full_rank_family=$family > "$OUT/family$family.log" 2>&1
  cat "$OUT/family$family.log"
 done
fi
