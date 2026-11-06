#!/usr/bin/env python3
"""HBM-GAPS-5-LEC: opt-in (`ifdef OT_Q2NF_TGTQ1) single-register form of u_program.target_q in ot_q2nf_rest.
Same class as OT_Q3CTL_TGTQ1 (HBM-GAPS-5-BODYCTL, ot_hfd_coll_q3_body_ctl).
Old: reg [7:0] _55083_ <= target_eff, target_eff = hit ? 8'h34 : 8'h00 (no reset, hit = _23041_).  Bits 0,1,3,6,7 are
constant 0 after the first edge and bits 2,4,5 are three copies of one flop; synthesis keeps one, the gold keeps three,
so the kit LEC could not match gold-only _55083_[2] (2017 differ).  New: one 1-bit register of hit, constant bits wires."""
import sys
p = sys.argv[1]
s = open(p).read()
assert "OT_Q2NF_TGTQ1" not in s, "already patched"
P = "  reg [7:0] _55083_;\n  always @(posedge clk_program)\n    _55083_ <= "
i = s.index(P)
assert s.count("reg [7:0] _55083_;") == 1
j = s.index("\n", s.index("= _55083_;", i)) + 1
old = s[i:j]
assert old.count("\n") == 4, old[:300]
hit = "_23041_"
assert s.count(hit) == 3
assert "_23041_ ? 8'h34 : 8'h00;" in s
tq = "\\u_body.g_q2.n_u_fj.u_fj.u.u_program.target_q[%d] "
lhs = "{ " + " , ".join(tq % b for b in range(7, -1, -1)) + " }"
new = ("`ifdef OT_Q2NF_TGTQ1\n"
       "  // HBM-GAPS-5-LEC: target_eff = hit ? 8'h34 : 8'h00 -> one register of hit; bits 0,1,3,6,7 tied 0.\n"
       "  reg q2nf_tgt_hit_q;\n"
       "  always @(posedge clk_program)\n"
       "    q2nf_tgt_hit_q <= " + hit + ";\n"
       "  assign " + lhs + " = { 2'b00, q2nf_tgt_hit_q, q2nf_tgt_hit_q, 1'b0, q2nf_tgt_hit_q, 2'b00 };\n"
       "`else\n" + old + "`endif\n")
s = s[:i] + new + s[j:]
open(p, "w").write(s)
print("patched", p)
