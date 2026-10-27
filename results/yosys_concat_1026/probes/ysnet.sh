#!/bin/bash
# ysnet.sh SRC TOP PARAMS OUT : flow frontend (read_verilog -sv) + prep (no ABC) -> gate netlist module TOP_ys
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
c=""; for kv in $3; do c="$c -set ${kv%%=*} ${kv#*=}"; done
$Y -q -p "read_verilog -sv $1; chparam$c $2; prep -flatten -top $2; async2sync; opt_clean; rename $2 ${2}_ys; write_verilog -noattr $4" > $4.log 2>&1 && echo "NET $4 ok" || { echo "NET $4 FAIL"; tail -3 $4.log; }
