#!/bin/bash
set -euo pipefail
D=$(pwd)
for width in 328 257; do
 docker run --rm -v "$D:/coupon" -w /coupon openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -p 'read_verilog -formal -sv src/ot_hbm_parent_station32.sv src/formal_hbm_parent_station32.sv; chparam -set W $width formal_hbm_parent_station32; prep -top formal_hbm_parent_station32 -flatten; async2sync; opt_clean; sat -seq 8 -prove-asserts -verify'" > "proofs/formal_$width.log" 2>&1
done
