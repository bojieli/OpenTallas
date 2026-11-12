#!/usr/bin/env python3
"""Take ft_slots of the listed types from the ft_nudge output into the composed plan (every other type untouched).
    take_slots.py COMPOSED NUDGED TYPES_JSON[,..] OUT [--drop T1,T2]   (--drop: types whose VIS positions are reverted)"""
import json, sys
c, n, tl, out = sys.argv[1:5]
drop = sys.argv[sys.argv.index("--drop") + 1].split(",") if "--drop" in sys.argv else []
base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else None
C = json.load(open(c)); N = json.load(open(n))
B = json.load(open(base)) if base else None
types = [t for f in tl.split(",") for t in json.load(open(f))]
rep = {}
for tn in types:
    if tn in drop:
        C["partition_types"][tn] = B["partition_types"][tn]; rep[tn] = "reverted to base"; continue
    a = C["partition_types"][tn]; b = N["partition_types"][tn]
    ch = [s["name"] for s, s2 in zip(a.get("ft_slots") or [], b.get("ft_slots") or []) if s != s2]
    assert [s["name"] for s in a.get("ft_slots") or []] == [s["name"] for s in b.get("ft_slots") or []]
    for s, s2 in zip(a.get("ft_slots") or [], b.get("ft_slots") or []):
        assert s.get("stations", 1) == s2.get("stations", 1) and s["width"] == s2["width"]
    a["ft_slots"] = b.get("ft_slots"); rep[tn] = ch
ind = 1 if open(c).read(2) == "{\n" else None
open(out, "w").write(json.dumps(C, indent=ind) + "\n")
for k, v in rep.items():
    print(k, v)
