#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../.."
out=${1:?output directory required}
mkdir -p "$out"
src=rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv
tb=rtl/dsrom_sys/s81_die_bind/test/tb_static_lane_cross.sv
for phase in 1 2 4 6 8 9; do
  iverilog -g2012 -s tb_static_lane_cross -Ptb_static_lane_cross.PHASE="$phase" -o "$out/run" "$src" "$tb"
  vvp "$out/run"
done
iverilog -g2012 -s tb_static_lane_cross -Ptb_static_lane_cross.RSLIP=1 -o "$out/slip" "$src" "$tb"
vvp "$out/slip"
iverilog -g2012 -DOT_S81_STATIC_CROSS_MUT_OFFSET -s tb_static_lane_cross -o "$out/mut" "$src" "$tb"
if vvp "$out/mut" > "$out/mut.log" 2>&1; then
  echo 'static crossing mutant escaped' >&2; exit 1
fi
grep -E 'data mismatch' "$out/mut.log"
echo 'STATIC_LANE_CROSS_GATE PASS six phases, reset epochs, slip fault, offset mutant rejected'
