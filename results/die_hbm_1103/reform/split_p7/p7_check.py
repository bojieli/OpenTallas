#!/usr/bin/env python3
"""DIE-HBM-62/BIG part 7: the generated flat composition has the same wiring as the EQ-proven SPLIT composition.
Compares, per sub instance and sub port bit, the top pin bits and peer instances from split_conn.py of both elaborations
(instance names mapped: g_ln[p].u_tl0 -> u_ln<p>_tl0, g_p[q].u_p -> u_p<q>).
    p7_check.py ORIG.conn.json FLAT.conn.json   (exit 1 on any difference)"""
import json, re, sys
A, B = (json.load(open(f)) for f in sys.argv[1:3])
def mp(n):
    n = re.sub(r"g_ln\[(\d)\]\.u_", r"u_ln\1_", n)
    return re.sub(r"g_p\[(\d)\]\.u_p", r"u_p\1", n)
pre = lambda n: re.sub(r"^.*?u_core\.", "", n)
def norm(C):
    o = {}
    for s in C["subs"]:
        o[mp(pre(s["inst"]))] = {nm: (b["top"], sorted(mp(pre(q)) for q in b["peer"])) for nm, b in s["bits"].items()}
    return o
a, b = norm(A), norm(B)
assert sorted(a) == sorted(b), (sorted(a), sorted(b))
bad = [(i, nm) for i in a for nm in set(a[i]) | set(b[i]) if a[i].get(nm) != b[i].get(nm)]
print(len(a), "subs", sum(len(v) for v in a.values()), "bits", "DIFF", len(bad), bad[:5])
sys.exit(1 if bad else 0)
