#!/usr/bin/env python3
"""HBM-FORM-SPLIT-3 part 27r: opsa_rest fault cycles. The memory fault flag's own terms (bad_source, bad_range, scalar_bad, 218 AND terms OR-ed in
three priority chains) span the whole 760 um tile in one cycle: rd_re pins sit at x 753, rd_src at x 0-383, vm_we and stage_v at x 0, rd_addr at x 606-753.
They get three register stages: one flop per term, one OR flop per 8 terms of a chain, one flop for all; then the sticky fault flop.
group_fault[*] keep their date. The fault flag is sticky and leaves the core only as a flag: +3 cycles on these terms, 0 elsewhere.
Usage: mk_rest_p27r.py REST.sv  (rewrites in place, refuses a second run)"""
import re, sys
F = sys.argv[1]
s = open(F).read()
assert "fp_term_q" not in s
end = s.index("endmodule")
body, rest = s[:end], s[end:]
L = body.split("\n")
A = {}
for i, l in enumerate(L):
    m = re.match(r"\s*assign (\S+)\s*=\s*(.*);\s*$", l)
    if m: A[m[1]] = (i, m[2])
RST = "\\u_core.u_rst.relay_q[0][1] "
ROOTS = ["\\u_core.u_engine.u_memory.bad_source", "\\u_core.u_engine.u_memory.bad_range", "\\u_core.u_engine.u_memory.scalar_bad"]
drop, chains = set(), []
for r in ROOTS:
    n, cs = r, []
    while n != "1'h0":
        i, e = A[n]
        m = re.match(r"(\S+) \? 1'h1 : (\S+)$", e)
        assert m, (n, e)
        cs.append(m[1]); drop.add(i); n = m[2]
    chains.append(cs)
assert [len(c) for c in chains] == [64, 90, 64], [len(c) for c in chains]
# the chain nodes must feed nothing else
names = {L[i].split()[1] for i in drop}
for i, l in enumerate(L):
    if i in drop or not l.lstrip().startswith("assign"): continue
    rhs = l.split("=", 1)[1]
    for t in re.findall(r"\\\S+|_\d+_", rhs):
        if t in names and not (L[i].split()[1] == "_3328_" or L[i].split()[1] == "_3329_"):
            raise SystemExit("chain node used elsewhere: %s in %s" % (t, l[:100]))
for n in ("_3328_", "_3329_"):
    assert n in A; drop.add(A[n][0])
assert A["_3330_"][1] == "_3329_ || _3539_"
L[A["_3330_"][0]] = "  assign _3330_ = fp_all_q || _3539_;"
terms = [c for ch in chains for c in ch]
assert len(set(terms)) == len(terms)
idx = {c: i for i, c in enumerate(terms)}
N = len(terms); groups = []
for ch in chains:
    for a in range(0, len(ch), 8):
        groups.append([idx[c] for c in ch[a:a + 8]])
M = len(groups)
decl = ["  // part 27r: fault terms, three register stages (see mk_rest_p27r.py)",
        "  reg [%d:0] fp_term_q;" % (N - 1), "  reg [%d:0] fp_seg_q;" % (M - 1), "  reg fp_all_q;"]
new = ["  always @(posedge clk, negedge %s) begin" % RST,
       "    if (!%s) begin fp_term_q <= %d'h0; fp_seg_q <= %d'h0; fp_all_q <= 1'h0; end" % (RST, N, M),
       "    else begin"]
new += ["      fp_term_q[%d] <= %s;" % (i, c) for i, c in enumerate(terms)]
new += ["      fp_seg_q[%d] <= %s;" % (g, " || ".join("fp_term_q[%d]" % i for i in G)) for g, G in enumerate(groups)]
new += ["      fp_all_q <= | fp_seg_q;", "    end", "  end"]
keep = [l for i, l in enumerate(L) if i not in drop]
# wires of removed nodes go too
gone = names | {"_3328_", "_3329_"}
keep = [l for l in keep if not (re.match(r"\s*wire (\S+)\s*;\s*$", l) and re.match(r"\s*wire (\S+)\s*;\s*$", l)[1] in gone)]
first = next(i for i, l in enumerate(keep) if l.lstrip().startswith("assign "))
keep[first:first] = decl
open(F, "w").write("\n".join(keep + new) + "\n" + rest)
print("terms", N, "segs", M, "dropped assigns", len(drop), "added flops", N + M + 1)
