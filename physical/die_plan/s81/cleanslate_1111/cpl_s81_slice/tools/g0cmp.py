#!/usr/bin/env python3
"""compare two G0 reports: new ERROR findings (by check + msg) in AFTER that are not in BEFORE; also new WARNs that
name one of the given types.  usage: g0cmp.py BEFORE.json AFTER.json [TYPE...]"""
import json
import sys

b, a = (json.load(open(p)) for p in sys.argv[1:3])
types = sys.argv[3:]


def keyset(r, lvl):
    return {(f.get("check"), f.get("msg")) for f in r["findings"] if f.get("level") == lvl}


eb, ea = keyset(b, "ERROR"), keyset(a, "ERROR")
wb, wa = keyset(b, "WARN"), keyset(a, "WARN")
newe = sorted(ea - eb)
gone = sorted(eb - ea)
neww = sorted(w for w in wa - wb if any(t in (w[1] or "") for t in types))
print("ERROR before", len(eb), "after", len(ea), "NEW", len(newe), "cleared", len(gone))
for e in newe[:30]:
    print("  NEW", e[0], (e[1] or "")[:300])
for e in gone[:30]:
    print("  CLEARED", e[0], (e[1] or "")[:300])
print("WARN naming my types: NEW", len(neww))
for w in neww[:40]:
    print("  NEWW", w[0], (w[1] or "")[:300])
