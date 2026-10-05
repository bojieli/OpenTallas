#!/bin/sh
# Prove the balanced reduction tree identical to the serial-accumulation version
# it replaces, over every input, by SAT miter in the pinned Yosys.
#
#   $ tools/prove_reduction_tree_equivalence.sh
#   SAT proof finished - no model found: SUCCESS!
#
# Integer addition is associative, so a different grouping cannot change the sum
# -- but the widths, the sign extension of a masked-off source and the overflow
# flag all have to be right too, and those are what a proof checks and an
# argument does not.
set -e
cd "$(dirname "$0")/.."
YOSYS="${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}"
"$YOSYS" -p '
read_verilog -sv rtl/ot_reduction_tree.sv
read_verilog -sv rtl/test/golden/ot_reduction_golden.sv
hierarchy -check
proc; opt_expr; opt_clean
miter -equiv -make_assert ot_reduction_tree_golden ot_reduction_tree miter
hierarchy -top miter
flatten; opt -fast
sat -verify -prove-asserts miter
' 2>&1 | grep -E 'SAT proof|Solving problem'
