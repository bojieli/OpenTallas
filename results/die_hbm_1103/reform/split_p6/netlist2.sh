#!/bin/bash
# netlist2.sh OUTJSON TOP GLUE.sv COMPOSITION.sv SUB.sv...   (glue + composition elaborated, subs blackboxed)
set -e
O=$1; TOP=$2; G=$3; C=$4; shift 4
T=$(mktemp -d); sed 's/__fs\b//g' "$C" > $T/comp.sv
L=""; for f in "$@"; do L="$L read_verilog -sv -lib $f;"; done
$HOME/.local/opentallas-tools/bin/yosys -q -p "$L read_verilog -sv $T/comp.sv $G; hierarchy -top $TOP; proc; flatten; opt_clean; write_json $O" > $T/log 2>&1 || { tail -5 $T/log; exit 1; }
rm -rf $T
