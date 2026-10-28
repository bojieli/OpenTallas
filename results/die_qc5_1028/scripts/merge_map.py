#!/usr/bin/env python3
"""DIE-QC-5 (COORD 04:0x): merge each child region into its feed parent (the 3 CA-FAIL region pairs).
usage: merge_map.py MAP FEED OUT_MAP OUT_FEED CHILD=PARENT ..."""
import json, sys
mp, fd, om, of = sys.argv[1:5]
pairs = [a.split("=") for a in sys.argv[5:]]
M = json.load(open(mp)); F = json.load(open(fd))
pr, par, tap = M["part_region"], F["parent"], F["tap"]
for ch, pa in pairs:
    assert par.get(ch) == pa, (ch, par.get(ch), pa)
    for p, r in list(pr.items()):
        if r == ch:
            pr[p] = pa
    del par[ch]
    tap.pop(f"{pa}->{ch}")
    for c, p in list(par.items()):
        if p == ch:
            par[c] = pa
            tap[f"{pa}->{c}"] = tap.pop(f"{ch}->{c}")
    F.setdefault("joined", []).append([ch, pa])
M["note"] = M.get("note", "") + " | DIE-QC-5: merged " + ", ".join(f"{c}->{p}" for c, p in pairs) + " (COORD 04:0x, 6 CA FAILs)"
json.dump(M, open(om, "w"), indent=1); json.dump(F, open(of, "w"), indent=1)
print("regions", len(set(pr.values())), "feed edges", sum(1 for v in par.values() if v), "taps", len(tap))
