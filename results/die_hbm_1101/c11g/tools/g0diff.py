#!/usr/bin/env python3
"""g0diff.py BASE_REPORT NEW_REPORT: ERROR/WARN findings new vs gone (by level+check+msg)."""
import json, sys, collections
def load(p):
    d = json.load(open(p)); return d, collections.Counter((f["level"], f["check"], f["msg"]) for f in d["findings"])
(bd, b), (nd, n) = load(sys.argv[1]), load(sys.argv[2])
print("base", bd["summary"] if isinstance(bd["summary"], str) else json.dumps(bd["summary"])[:200])
print("new ", nd["summary"] if isinstance(nd["summary"], str) else json.dumps(nd["summary"])[:200])
for tag, c in (("NEW", n - b), ("GONE", b - n)):
    lv = collections.Counter(k[0] for k in c.elements()); print(tag, dict(lv))
    for k in sorted(c, key=lambda k: k[0])[:int(sys.argv[3]) if len(sys.argv) > 3 else 12]:
        if k[0] == "ERROR" or len(sys.argv) > 3: print("  ", tag, k[0], k[1], k[2][:260])
