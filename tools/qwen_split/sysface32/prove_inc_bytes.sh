#!/bin/bash
# prove_inc_bytes.sh (FABLE-FIX-S81-GLUE 2026-11-19): the kept-byte-carry incrementers of qfd_sys_face_lctx3_core
# (tcyc_inc, pos_inc) equal tcyc + 1 and pos + 1 for every value.  The expressions are read from the core file itself.
set -eu
cd "$(dirname "$0")/../../.."
Y=${YOSYS:-/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys}
O=${1:-bench/inc_bytes}; mkdir -p "$O"
F=rtl/qwen_split/qfd_sys_face_lctx3_core.sv
{ echo 'module inc_bytes(input [31:0] tcyc, input [17:0] pos, output bad);'
  awk '/\(\* keep \*\) wire \[2:0\] tcyc_b1/,/wire \[17:0\] pos_inc/' "$F"
  echo "assign bad = (tcyc_inc != tcyc + 32'd1) || (pos_inc != pos + 18'd1);"
  echo endmodule; } > "$O/inc_bytes.sv"
grep -q 'tcyc <= tcyc_inc;' "$F" && grep -q 'pos <= pos_inc;' "$F"
test "$(grep -c 'wire' "$O/inc_bytes.sv")" = 6
"$Y" -Q -q -l "$O/sat.log" -p "read_verilog -sv $O/inc_bytes.sv; prep -top inc_bytes; sat -verify -prove bad 0" >/dev/null 2>&1 || { tail -5 "$O/sat.log"; echo INC_BYTES_FAIL; exit 1; }
grep -q 'SAT proof finished - no model found: SUCCESS!' "$O/sat.log"
echo INC_BYTES_PASS
