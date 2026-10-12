#!/bin/bash
set -eu
out=$1; mutant=${2:-0}; mkdir -p "$out"
cd "$(dirname "$0")/../.."
iverilog -g2012 -s tb_pair_wiring -Ptb_pair_wiring.MUT="$mutant" -o "$out/wiring.vvp" \
 physical/hbm_coll_port2_tiles_20261010/tb_pair_wiring.sv physical/hbm_coll_port2_tiles_20261010/ot_hcoll_port2_tiles.sv
vvp -n "$out/wiring.vvp"
