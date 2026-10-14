#!/bin/bash
set -eu
SRC=$1
OUT=$2
MODE=${3:-pass}
mkdir -p "$OUT"
FILES=("$SRC/rtl/dsrom_sys/s81_glue/ot_s81_rly.sv" "$SRC/rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv" "$SRC/rtl/dsrom_sys/s81_ph/dsfd_gth_strip.sv" "$SRC/rtl/dsrom_sys/s81_ph/test/tb_s81ph_gather_strip.sv")
sha256sum "${FILES[@]}" > "$OUT/sources.sha256"
DEFS=()
if [ "$MODE" = mut ]; then DEFS=(+define+OT_S81_RLY_MUT); fi
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_s81ph_gather_strip "${DEFS[@]}" --Mdir "$OUT/obj" -o sim "${FILES[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/sim" > "$OUT/run.log" 2>&1
