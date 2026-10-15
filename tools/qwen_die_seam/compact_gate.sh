#!/bin/bash
set -euo pipefail
out=${1:?output directory}; mode=${2:-pass}
mkdir -p "$out"
defines=()
case "$mode" in
  pass) depths=$(seq 0 21);;
  drop) depths=21;defines=(-DOT_QTREE_MUT_DROP);;
  flip) depths=21;defines=(-DOT_QTREE_MUT_FLIP);;
  *) exit 2;;
esac
for depth in $depths; do
  iverilog -g2012 -s tb_compact_delay -Ptb_compact_delay.LAT="$depth" "${defines[@]}" \
    -o "$out/delay_$depth" tools/qwen_die_seam/tb_compact_delay.sv rtl/physical/ot_qwen_tree_delay.sv
  vvp "$out/delay_$depth"
done
