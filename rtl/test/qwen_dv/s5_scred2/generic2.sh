#!/usr/bin/env bash
# generic netlist with yosys' default synth passes (share/fsm on), then dffunmap: OUT TOP "chparam" SRC...
set -euo pipefail
O=$1; TOP=$2; CHP=$3; shift 3; mkdir -p "$O"
CH=""; [[ -z "$CHP" ]] || CH="chparam $CHP $TOP;"
yosys -Q -p "read_verilog -sv -D SYNTHESIS $*; $CH hierarchy -check -top $TOP; synth -top $TOP -flatten -noabc; dffunmap; clean; write_json $O/generic.json" > "$O/generic.log" 2>&1
echo GENERIC2_DONE
