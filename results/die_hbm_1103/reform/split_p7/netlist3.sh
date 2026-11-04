#!/bin/bash
# netlist3.sh OUTJSON TOP GLUE.sv COMP.sv SUB.sv...  (glue + generated composition elaborated, subs blackboxed)
set -e
O=$1; TOP=$2; G=$3; C=$4; shift 4
T=$(mktemp -d); L=""; for f in "$@"; do L="$L read_verilog -sv -lib $f;"; done
$HOME/.local/opentallas-tools/bin/yosys -q -p "$L read_verilog -sv $C $G; hierarchy -top $TOP; proc; flatten; opt_clean; write_json $O" > $T/log 2>&1 || { tail -5 $T/log; rm -rf $T; exit 1; }
rm -rf $T
