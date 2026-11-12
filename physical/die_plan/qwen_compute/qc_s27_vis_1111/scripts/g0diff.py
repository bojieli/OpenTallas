#!/usr/bin/env python3
"""G0 / G0C ERROR+WARN diff base vs cand (exact message multiset, plus per-type new ERROR list).  g0diff.py BASE.json CAND.json"""
import json, sys, collections, re
a, b = (json.load(open(p)) for p in sys.argv[1:3])
def items(d, sev):
    return [f for f in d["findings"] if str(f.get("level", f.get("severity", ""))).upper().startswith(sev)]
for sev in ("ERR", "WARN"):
    A = collections.Counter((f["check"], f["msg"]) for f in items(a, sev)); B = collections.Counter((f["check"], f["msg"]) for f in items(b, sev))
    new = B - A; gone = A - B
    print(f"== {sev}: base {sum(A.values())} cand {sum(B.values())} new {sum(new.values())} gone {sum(gone.values())}")
    for (c, m), n in sorted(new.items()):
        print(f"  NEW x{n} [{c}] {m[:300]}")
    for (c, m), n in sorted(gone.items()):
        print(f"  GONE x{n} [{c}] {m[:300]}")
