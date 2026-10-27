#!/bin/bash
# usage: probe.sh dir  (inside docker). For each m_*.sv: read_verilog -sv vs read_slang equivalence.
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
cd $1
for f in m_*.sv; do m=${f%.sv}
 $Y -q -p "read_verilog -sv $f; prep -top $m; rename $m gold_rv; design -stash rv; read_slang $f --top $m; prep -top $m; rename $m gate_sl; design -stash sl; design -copy-from rv -as rv gold_rv; design -copy-from sl -as sl gate_sl; miter -equiv -flatten -make_outputs rv sl miter; hierarchy -top miter; sat -verify -prove trigger 0 -show-inputs -show-outputs miter" > $m.log 2>&1 && echo "$m EQ" || echo "$m DIFF"
done
