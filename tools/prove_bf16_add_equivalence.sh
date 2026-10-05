#!/bin/sh
# Prove ot_bf16_add_flat bit-identical to ot_bf16_add_rne over ALL 2**32 input
# pairs, by SAT miter in the pinned Yosys.  Not a sampled test: the solver either
# finds an input pair where the two disagree, or proves none exists.
#
#   $ tools/prove_bf16_add_equivalence.sh
#   SAT proof finished - no model found: SUCCESS!
#
# A restructured float adder is exactly the kind of change where a directed
# testbench passes and a carry or a sticky bit is still wrong in one corner of
# the exponent range, so the equivalence is proven rather than sampled.
set -e
cd "$(dirname "$0")/.."
YOSYS="${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}"
"$YOSYS" -p '
read_verilog -sv rtl/ot_bf16_add_rne.sv
read_verilog -sv rtl/proto/ot_bf16_add_flat.sv
hierarchy -check
proc; opt_expr; opt_clean
miter -equiv -make_assert ot_bf16_add_rne ot_bf16_add_flat miter
hierarchy -top miter
flatten; opt -fast
sat -verify -prove-asserts miter
' 2>&1 | grep -E 'SAT proof|Solving problem'
