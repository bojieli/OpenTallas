#!/usr/bin/env bash
set -euo pipefail
base=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(cd "$base/../../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
src=("$base/s81_static_fmt1_channels_clocked.sv" "$base/s81_static_raw_fmt1_codec.sv" "$base/s81_static_raw_fmt1_lane.sv" "$base/s81_static_fmt1_gearbox.sv" "$base/s81_static_fmt1_channels.sv" "$root/rtl/dsrom_sys/s81_ph/coll/dsfd_coll_static_channels.sv" "$root/rtl/link/ot_link_crc32.sv" "$root/rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv")
# Existing dependency warnings: wide CRC masks and intentionally unused padding.
verilator --lint-only -Wall -Wno-WIDTHCONCAT -Wno-UNUSED -Wno-VARHIDDEN --top-module s81_static_fmt1_channels "${src[@]}"
iverilog -g2012 -s tb_s81_static_raw_fmt1_codec -o "$work/codec" "${src[@]}" "$base/tb_s81_static_raw_fmt1_codec.sv"
vvp "$work/codec"
iverilog -g2012 -s tb_s81_static_fmt1_channels -o "$work/good" "${src[@]}" "$base/tb_s81_static_fmt1_channels.sv"
vvp "$work/good"
iverilog -g2012 -s tb_s81_static_fmt1_channels -Ptb_s81_static_fmt1_channels.CLOCKED=1 -o "$work/clocked" "${src[@]}" "$base/tb_s81_static_fmt1_channels.sv"
vvp "$work/clocked"
echo 'PASS delivered separate adapter/lane clocks with declared same-phase component calendar; physical phases unqualified' 
iverilog -g2012 -s tb_s81_static_fmt1_channels -Ptb_s81_static_fmt1_channels.MUT=1 -o "$work/bad" "${src[@]}" "$base/tb_s81_static_fmt1_channels.sv"
if vvp "$work/bad" > "$work/mutant.log" 2>&1; then echo 'FAIL actual CRC mutant survived';exit 1;fi
if ! grep -Eq 'composition fault|legacy full552' "$work/mutant.log";then cat "$work/mutant.log";exit 1;fi
cat "$work/mutant.log"
echo 'PASS actual DUT CRC output mutant rejected'
sha256sum "${src[@]}" "$base/tb_s81_static_fmt1_channels.sv" "$base/tb_s81_static_raw_fmt1_codec.sv"
