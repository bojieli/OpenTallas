#!/usr/bin/env python3
"""HBM-GAPS-5-BODYCTL: opt-in (`ifdef OT_Q3CTL_TGTQ1) single-register form of u_program.target_q.
Old: reg [7:0] _237836_ <= target_eff, target_eff = hit ? 8'h34 : 8'h00 (no reset).  Bits 0,1,3,6,7 are constant 0
after the first edge and bits 2,4,5 are three copies of one flop; synthesis keeps one, the gold keeps three, so the
kit LEC cannot match gold-only _237836_[2].  New: one 1-bit register of `hit`, the constant bits are wires."""
import sys
p = sys.argv[1]
s = open(p).read()
P = "  reg [7:0] _237836_;\n  always @(posedge clk_program)\n    _237836_ <= "
i = s.index(P)
assert s.count("reg [7:0] _237836_;") == 1
j = s.index("\n", s.index("= _237836_;", i)) + 1
old = s[i:j]
assert old.count("\n") == 4, old[:300]
hit = "_018274_"
assert s.count(hit) == 3
tq = "\\u_body.g_q3.n_u_fj.u_fj.u.u_program.target_q[%d] "
lhs = "{ " + " , ".join(tq % b for b in range(7, -1, -1)) + " }"
new = ("`ifdef OT_Q3CTL_TGTQ1\n"
       "  // HBM-GAPS-5-BODYCTL: target_eff = hit ? 8'h34 : 8'h00 -> one register of hit; bits 0,1,3,6,7 tied 0.\n"
       "  reg q3ctl_tgt_hit_q;\n"
       "  always @(posedge clk_program)\n"
       "    q3ctl_tgt_hit_q <= " + hit + ";\n"
       "  assign " + lhs + " = { 2'b00, q3ctl_tgt_hit_q, q3ctl_tgt_hit_q, 1'b0, q3ctl_tgt_hit_q, 2'b00 };\n"
       "`else\n" + old + "`endif\n")
s = s[:i] + new + s[j:]
open(p, "w").write(s)
print("patched", p)
