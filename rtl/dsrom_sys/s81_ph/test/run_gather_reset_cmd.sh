#!/bin/bash
set -eu
SRC=$1
OUT=$2
mkdir -p "$OUT"
P=$SRC/rtl/dsrom_sys
MODE=${3:-pass}
DEFS=()
if [ "$MODE" = mut ]; then DEFS=(+define+S81PH_GTH_MUT_BOOTDROP); fi
FILES=("$P/s81_ph/dsfd_gth_strip.sv" "$P/s81_glue/ot_s81_rly.sv" "$P/s81_glue/dsfd_rly_masters.sv" "$P/s81_ph/dsfd_gth_ctl.sv" "$P/s81_ctrl/ot_s81_slab_ep.sv" "$P/s81_ctrl/ot_s81_engine_adapter.sv" "$SRC/rtl/common/ot_ratio_cdc_fifo.sv" "$SRC/rtl/lib/ot_async_fifo.sv" "$SRC/rtl/lib/ot_reset_sync.sv" "$P/s81_ph/test/tb_s81ph_gather_reset_cmd.sv")
sha256sum "${FILES[@]}" > "$OUT/sources.sha256"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_s81ph_gather_reset_cmd "${DEFS[@]}" --Mdir "$OUT/obj" -o sim "${FILES[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/sim" > "$OUT/run.log" 2>&1
