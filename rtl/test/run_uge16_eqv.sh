#!/bin/bash
# el1011-q-seq (2026-10-11): formal check of the PCUT log-depth comparator uge16 against a >= b (all 2^32 inputs, yosys SAT).
# usage: run_uge16_eqv.sh <outdir> <rtl file holding uge16> <PCUT>   (PCUT 1 must PASS; PCUT 3 = strict > mutant must FAIL)
set -e
O=$1; F=$2; P=$3; mkdir -p "$O"
python3 - "$F" "$P" "$O/uge16_chk_$P.v" <<'PY'
import sys
s = open(sys.argv[1]).read(); i = s.index('    function automatic uge16'); j = s.index('endfunction', i) + len('endfunction')
open(sys.argv[3], 'w').write(f"module chk(input [15:0] a, input [15:0] b, output ok);\n    localparam integer PCUT = {sys.argv[2]};\n"
                             f"{s[i:j]}\n    assign ok = (uge16(a, b) == (a >= b));\nendmodule\n")
PY
if yosys -q -p "read_verilog -sv $O/uge16_chk_$P.v; prep -top chk; flatten; sat -prove ok 1 -verify" > "$O/uge16_eqv_$P.log" 2>&1; then
    echo "PASS uge16_eqv PCUT=$P (uge16 == >= for all 2^32 inputs)"
else
    echo "FAIL uge16_eqv PCUT=$P"; exit 1
fi
