#!/bin/bash
# exact / mutant bench of ONE hard delay wrapper ot_qwen_tree_delay<N>_t: tile_gate.sh <out> <N> pass|drop|flip
set -euo pipefail
out=${1:?output directory}; depth=${2:?depth}; mode=${3:-pass}
mkdir -p "$out"
defines=()
case "$mode" in
  pass) ;;
  drop) defines=(-DOT_QTREE_MUT_DROP);;
  flip) defines=(-DOT_QTREE_MUT_FLIP);;
  *) exit 2;;
esac
iverilog -g2012 -s tb_tree_delay_tile -Ptb_tree_delay_tile.LAT="$depth" "${defines[@]}" -o "$out/tile_$depth" \
  tools/qwen_die_seam/tb_tree_delay_tile.sv rtl/physical/ot_qwen_tree_delay_tiles.sv rtl/physical/ot_qwen_tree_delay.sv
vvp "$out/tile_$depth"
