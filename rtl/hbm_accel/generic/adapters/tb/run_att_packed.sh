#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); mkdir -p "$OUT"; cd "$ROOT"
python3 tools/hgi_adapters/att_packed_bench.py "$OUT/vec"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
 --top-module tb_hgi_att_packed -I"$OUT/vec" -Mdir "$OUT/obj" -j "${J:-4}" \
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_att_unit.sv rtl/hbm_accel/generic/peers/ot_hgi_att_sector_codec.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_att_selected_bridge.sv rtl/hbm_accel/generic/adapters/tb/tb_hgi_att_packed.sv \
 > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_att_packed" +DIR="$OUT/vec" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
