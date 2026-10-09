#!/bin/bash
# Admitted remote only. VECTORS contains owner's input.hex and expected.hex.
set -euo pipefail
SRC=$1;OUT=$2;VECTORS=$3
test ! -e "$OUT" || { echo 'Refuse existing evidence directory' >&2;exit 2; }
mkdir -p "$OUT"
FILES=("$SRC/rtl/hdc/ot_hdc_prefix.sv" "$SRC/rtl/hdc/ot_hdc_fastfp.sv"
 "$SRC/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$SRC/rtl/hdc/ot_hdc_fp32_mul_lat.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv"
 "$SRC/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
 "$SRC/rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_mean_capture.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_hc_cmd_bridge.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/test/tb_s81_hc_cmd_bridge.sv")
sha256sum "${FILES[@]}" "$VECTORS/input.hex" "$VECTORS/expected.hex" > "$OUT/sources.sha256"
iverilog -g2012 -s tb_s81_hc_cmd_bridge -o "$OUT/bridge.vvp" "${FILES[@]}" > "$OUT/build.log" 2>&1
for mode in full orphan identity malformed;do
 case $mode in full)P="";;orphan)P="+bridge_bad=1";;identity)P="+bridge_bad=2";;malformed)P="+bad=4";;esac
 vvp "$OUT/bridge.vvp" +vectors="$VECTORS" $P > "$OUT/$mode.log" 2>&1
 cat "$OUT/$mode.log"
done
