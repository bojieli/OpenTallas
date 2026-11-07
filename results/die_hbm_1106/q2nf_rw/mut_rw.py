#!/usr/bin/env python3
"""mut_rw.py RTL_PATCHED OUT: old_w.sv = old side (default branch, renamed); n0.sv = new side; n1..n5 = mutants of the OT_Q2NF_RW branch (see bench_rw.sh).
The new side has the define resolved in the text, so the old side and the new side can share one verilator run."""
import re, sys
s = open(sys.argv[1]).read(); O = sys.argv[2]
IF = re.compile(r"`ifdef OT_Q2NF_RW\n(.*?)`else\n(.*?)`endif\n", re.S)
assert len(IF.findall(s)) == 14
old = IF.sub(r"\2", s); new = IF.sub(r"\1", s)
old = re.sub(r"\bot_q2nf_rest_x\b", "old_ot_q2nf_rest_x", old).replace("module ot_q2nf_rest (", "module old_ot_q2nf_rest (")
open(O + "/old_w.sv", "w").write(old); open(O + "/n0.sv", "w").write(new)
def inst(t, pat):
    m = re.search(r"^  ot_sram_1r1w_\S+_r0c0_g\d+ \\\S*" + pat + r"\S*\s+\(\n.*?^  \);\n", t, re.M | re.S); assert m, pat; return m
def swap01(body, port):
    m = re.search(r"\." + port + r"\(\{ (.*) \}\)", body); n = m.group(1).split(" , "); n[-1], n[-2] = n[-2], n[-1]
    return body[:m.start()] + "." + port + "({ " + " , ".join(n) + " })" + body[m.end():]
def flip0(body, port):
    m = re.search(r"\." + port + r"\(\{ (.*) \}\)", body); n = m.group(1).split(" , "); n[-1] = "~" + n[-1]
    return body[:m.start()] + "." + port + "({ " + " , ".join(n) + " })" + body[m.end():]
L = r"g_link\[0\]\.u_link\.g_bank\[1\]"; I = r"g_mem\[1\]\.u_bank\.u_sram_lo"
muts = {1: (L, lambda b: flip0(b, "r_addr_in")), 2: (L, lambda b: b.replace(".w_mask_in(1'h1)", ".w_mask_in(1'h0)")),
        3: (I, lambda b: swap01(b, "rd_out")), 4: (L, lambda b: swap01(b, "wd_in")), 5: (I, lambda b: flip0(b, "w_addr_in"))}
for k, (p, f) in muts.items():
    m = inst(new, p); b = f(m.group(0)); assert b != m.group(0), k
    open(f"{O}/n{k}.sv", "w").write(new[:m.start()] + b + new[m.end():])
print("mutants written", list(muts))
