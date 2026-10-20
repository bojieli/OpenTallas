#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
yosys --version > "$out/yosys_version.txt"
for shape in 283_6 26_49 32_42; do
 w=${shape%_*};d=${shape#*_}
 yosys -Q -p "read_verilog -sv -D SYNTHESIS rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/qwen_dv/s5/qfd_dv_s5_red_ring32.sv; chparam -set W $w -set D $d qfd_dv_s5_red_ring32; synth -top qfd_dv_s5_red_ring32 -flatten; write_json $out/$shape.json" > "$out/$shape.log" 2>&1
 python3 rtl/test/qwen_dv/red_ring32/census.py "$out/$shape.json" qfd_dv_s5_red_ring32 > "$out/${shape}_census.json"
done
