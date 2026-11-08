#!/bin/bash
set -euo pipefail
OUT=$1
MUT=${2:-0}
mkdir -p "$OUT"
S="$PWD/rtl"
"$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_svc_merge_h4 -Mdir "$OUT/obj" -j 4 -GMUT="$MUT" -CFLAGS -O1 \
 "$S/dsrom_sys/s81_dv/tb_svc_merge_h4.sv" "$S/dsrom_sys/s81_dv/ot_s81_svc_merge_h4.sv" \
 "$S/hdc/v41x/ot_hdc_v41x_attn_s.sv" "$S/hdc/v41x/ot_hdc_v41x_attn_tile.sv" "$S/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv" "$S/hdc/v41x/ot_hdc_v41x_kreg.sv" \
 "$S/hdc/ot_hdc_fp32_f12.sv" "$S/hdc/ot_hdc_prefix.sv" "$S/hdc/ot_hdc_fastfp.sv" "$S/hdc/ot_hdc_fp32_add_lat.sv" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_svc_merge_h4" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
