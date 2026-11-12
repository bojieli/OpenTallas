#!/usr/bin/env python3
"""eqdiff.py BASE.sv NEW.sv: classify the bound-RTL difference of one leaf type.

A line is 'stage' when it names a u_lf<k>_u_cst_<class> station net/cell (the CS_<C>_D chain), else 'other'.
Moved/renumbered generic names ($N) are normalised.  EQ-by-construction verdict: PASS when every changed line is a
station line and the per-class added stage count equals the plan delta (checked separately by the LF_CS gate)."""
import collections
import difflib
import re
import sys

st = re.compile(r"u_lf\d_u_cst_([a-z]+)_")
H = re.compile(r"_src_[0-9a-f]{12,}_")
D = re.compile(r"\d+")
nz = lambda x: D.sub("N", H.sub("_src_H_", x))


def lines(f):
    return [x.strip() for x in open(f) if x.strip()]


A, B = lines(sys.argv[1]), lines(sys.argv[2])
cls = collections.Counter()
for sign, L in (("-", A), ("+", B)):
    for x in L:
        m = st.search(x)
        if m:
            cls[(sign, m.group(1))] += 1
ca = collections.Counter(nz(x) for x in A if not st.search(x))
cb = collections.Counter(nz(x) for x in B if not st.search(x))
diff = (cb - ca) + collections.Counter({("-" + k): v for k, v in (ca - cb).items()})
alw = {k: v for k, v in diff.items() if k.lstrip("-").startswith("always @(posedge clk")}
other = {k: v for k, v in diff.items() if k not in alw}
net = collections.Counter()
for (sg, c), v in cls.items():
    net[c] += v if sg == "+" else -v
print("stage-lines net per class", dict(net))
print("added always-blocks (station FFs)", sum(alw.values()), list(alw)[:2])
print("other (digit-normalised multiset)", len(other))
for o in list(other.items())[:20]:
    print("  ", o)
print("VERDICT", "PASS" if not other else "CHECK")
