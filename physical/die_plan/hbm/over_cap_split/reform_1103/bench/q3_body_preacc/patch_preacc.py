#!/usr/bin/env python3
"""DIE-HBM-88-Q3C: opt-in (`ifdef OT_Q3CTL_PREACC) pre-registered reductions of u_program.data_q.
u_program.data_q (_237833_) is an unconditional, no-reset copy of u_fj.u.data_q on clk_program, so
|u_program.data_q[255:64] (_027460_, _027468_) and |u_program.data_q[63:57] (_027461_, _027469_) equal one register of the
same reduction taken on u_fj.u.data_q, on every cycle after the first edge.  The frame-accept condition then starts at a
flop Q instead of a 4-level 192-input reduction (vK TT worst: data_q[187] -> AND5/AND4 x4 -> accept -> assembly[1253])."""
import re, sys
p = sys.argv[1]
s = open(p).read()
U = "\\u_body.g_q3.n_u_fj.u_fj.u.data_q[%d] "
UP = "\\u_body.g_q3.n_u_fj.u_fj.u.u_program.data_q[%d] "
H = "  reg [255:0] _237833_;\n  always @(posedge clk_program)\n    _237833_ <= "
assert s.count(H) == 1
i = s.index(H)
j = s.index("\n", i + len(H))
dexp = s[i + len(H):j]
want = "{ " + ", ".join(U % b for b in range(255, -1, -1)) + " };"
assert dexp.strip() == want.strip(), "D of _237833_ is not u.data_q[255:0] in order"
k = s.index("\n", j + 1)
asg = s[j + 1:k]
want2 = "  assign { " + ", ".join(UP % b for b in range(255, -1, -1)) + " } = _237833_;"
assert asg.strip() == want2.strip(), "u_program.data_q is not _237833_"
# 4 reduction assigns
red = {}
for nm, hi, lo in (("_027460_", 255, 64), ("_027468_", 255, 64), ("_027461_", 63, 57), ("_027469_", 63, 57)):
    if hi == 255:
        old = "  assign %s = | { " % nm + ", ".join(UP % b for b in range(hi, lo - 1, -1)) + " };\n"
    else:   # (data_q[63:51] & MSPARE) != 0 as written by yosys: | { 19'h0, data_q[63:57], 6'h0 }
        old = "  assign %s = | { 19'h00000, " % nm + ", ".join(UP % b for b in range(hi, lo - 1, -1)) + ", 6'h00 };\n"
    assert s.count(old) == 1, nm
    red[nm] = (old, "ot_q3_pre_hz" if hi == 255 else "ot_q3_pre_ms")
for nm, (old, r) in red.items():
    s = s.replace(old, "`ifdef OT_Q3CTL_PREACC\n  assign %s = %s;\n`else\n" % (nm, r) + old + "`endif\n", 1)
blk = ("`ifdef OT_Q3CTL_PREACC\n"
       "  // DIE-HBM-88-Q3C: |data_q[255:64] and |data_q[63:57] of u_program, one edge early from u_fj.u.data_q (exact).\n"
       "  reg ot_q3_pre_hz, ot_q3_pre_ms;\n"
       "  always @(posedge clk_program) begin\n"
       "    ot_q3_pre_hz <= | { " + ", ".join(U % b for b in range(255, 63, -1)) + " };\n"
       "    ot_q3_pre_ms <= | { " + ", ".join(U % b for b in range(63, 56, -1)) + " };\n"
       "  end\n"
       "`endif\n")
# declare before the first use (the _027460_ block)
f = s.index("`ifdef OT_Q3CTL_PREACC\n  assign _027460_ = ")
assert f < s.index(H)
s = s[:f] + blk + s[f:]
open(p, "w").write(s)
print("patched", p)
