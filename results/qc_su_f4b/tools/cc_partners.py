#!/usr/bin/env python3
"""coupling partners of one net in a SPEF: partner net -> summed coupling fF (top 12)."""
import sys, collections
spef, want = sys.argv[1], sys.argv[2]
nm = {}; cur = None; sec = None; P = collections.Counter()
for l in open(spef):
    if l.startswith("*NAME_MAP"): sec = "map"; continue
    if sec == "map":
        if l.startswith("*") and l[1:2].isdigit(): k, v = l.split(None, 1); nm[k] = v.strip(); continue
        if l.strip() == "": continue
        sec = None
    if l.startswith("*D_NET"):
        cur = nm.get(l.split()[1], l.split()[1]) == want; sec = None; continue
    if not cur: continue
    if l.startswith("*CAP"): sec = "cap"; continue
    if l.startswith("*RES") or l.startswith("*END"):
        if l.startswith("*END"): break
        sec = None; continue
    f = l.split()
    if sec == "cap" and len(f) == 4:
        o = f[2].split(":")[0]; P[nm.get(o, o)] += 1e3 * float(f[3])
print(want, "total coupling %.2f fF to %d nets" % (sum(P.values()), len(P)))
for n, c in P.most_common(12): print("  %7.3f fF  %s" % (c, n))
