#!/usr/bin/env python3
"""Bench-only copy of ot_dshbm_spec_state_f_token_edge.sv for Verilator 5.032 (hgi-1010/h, 2026-10-10): the function
wrapfix(t, R) becomes a macro of the same expression (V3Delayed internal error 'Multiple Write refs on LHS of NBA'
on the inlined argument).  Same values: t is the function's 32-bit input, the result its 16-bit return.
    python3 wrapfix_copy.py SRC.sv OUT.sv"""
import re
import sys

s = open(sys.argv[1]).read()
a = s.index("function automatic [15:0] wrapfix")
b = s.index("endfunction", a) + len("endfunction")
s = s[:a] + s[b:]
s = re.sub(r"\bwrapfix\(", "`OT_WRAPFIX(", s)
m = ("`define OT_WRAPFIX(t, R) (($signed(32'(t)) >= $signed(32'(R))) ? 16'(32'(t) - 32'(R)) : "
     "($signed(32'(t)) < 0) ? 16'(32'(t) + 32'(R)) : 16'(32'(t)))\n")
open(sys.argv[2], "w").write(m + s)
