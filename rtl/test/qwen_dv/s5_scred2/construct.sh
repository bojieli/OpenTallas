#!/usr/bin/env bash
# generic synth + bounded constructor only (no map), e.g. for the mutant netlist. Usage: construct.sh OUT TOP NAME "chparam" "defines" SRC...
set -euo pipefail
O=$1; TOP=$2; NAME=$3; CHP=$4; DEFS=$5; shift 5; SRC="$*"; mkdir -p "$O"
CH=""; [[ -z "$CHP" ]] || CH="chparam $CHP $TOP;"
yosys -Q -p "read_verilog -sv -D SYNTHESIS $DEFS $SRC; $CH hierarchy -check -top $TOP; synth -top $TOP -flatten -noabc -nofsm -noshare; dffunmap; clean; write_json $O/generic.json" > "$O/generic.log" 2>&1
python3 tools/qwen_dv/bound_math_netlist.py "$O/generic.json" --load-cap 16 --transparent-inverters --retain-mux --shared-helpers --retain-all-comb --fuse-ao --top $TOP --name $NAME --out "$O/$NAME.sv" --helpers "$O/${NAME}_helpers.sv" --record "$O/model.json" > "$O/construct.log" 2>&1
rm -f "$O/generic.json"; echo CONSTRUCT_DONE
