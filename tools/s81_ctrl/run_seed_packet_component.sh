#!/bin/bash
# Remote minimum component; requires pinned native HC sources and golden vectors.
set -euo pipefail
SRC=${SRC:-$(pwd)}; OUT=$1; VECTORS=$2
HC_SOURCE=${HC_SOURCE:-$SRC/rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_mean_capture.sv}
HC_JOIN=${HC_JOIN:-$SRC/rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_seed_join.sv}
mkdir -p "$OUT"
EXTRA=(); if [[ ${ECC_PIPE:-0} == 1 ]]; then EXTRA=(-DHC_ECC_PIPE); fi
S=("$SRC/rtl/hdc/ot_hdc_prefix.sv" "$SRC/rtl/hdc/ot_hdc_fastfp.sv"
 "$SRC/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$SRC/rtl/hdc/ot_hdc_fp32_mul_lat.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv"
 "$SRC/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
 "$SRC/rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_secded_pipe.sv" "$HC_SOURCE" "$HC_JOIN" "$SRC/rtl/dsrom_sys/ot_dsrom_link_ct.sv"
 "$SRC/rtl/dsrom_sys/ot_dsrom_link_chan.sv" "$SRC/rtl/link/ot_link_crc32.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_ctrl_lane_adapter.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_seed_packet.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/test/tb_s81_seed_packet.sv")
sha256sum "${S[@]}" "$VECTORS/input.hex" "$VECTORS/expected.hex" > "$OUT/source.sha256"
iverilog -g2012 "${EXTRA[@]}" -DHC_DISTRIBUTED -s tb_s81_seed_packet -o "$OUT/base.vvp" "${S[@]}" > "$OUT/base.build" 2>&1
for bad in 0 1 2 3 4; do
 vvp "$OUT/base.vvp" +vectors="$VECTORS" +source_bad=$bad > "$OUT/bad$bad.log" 2>&1
done
iverilog -g2012 "${EXTRA[@]}" -DHC_DISTRIBUTED -DSEED_REPLAY -s tb_s81_seed_packet -o "$OUT/replay.vvp" "${S[@]}" > "$OUT/replay.build" 2>&1
vvp "$OUT/replay.vvp" +vectors="$VECTORS" > "$OUT/replay.log" 2>&1
