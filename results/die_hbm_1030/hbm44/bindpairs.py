#!/usr/bin/env python3
"""DIE-HBM-44: classify the strict-bind unplanned pairs (full bit list) by driver/sink group."""
import json, re, sys, collections
r = json.load(open(sys.argv[1])); L = r["lanes"]; ub = L["unplanned_bit_list"]
print("bits listed", len(ub), "pairs", len(L["unplanned_pairs"]), "total", sum(L["unplanned_pairs"].values()))
g = collections.defaultdict(int)
for b in ub:
    k = b["src_part"] + "->" + b["dst_part"]
    d = re.sub(r"\[\d+\]", "", b["driver"]); d = re.sub(r"\$\d+", "$N", d); d = re.sub(r"lane\d+", "laneK", d); d = re.sub(r":\d+", "", d)
    s = sorted(set(re.sub(r"\[\d+\]|\$\d+", "", x) for x in b["sink_ports"]))[:2]
    g[(k, d, tuple(s))] += 1
pairs = collections.defaultdict(list)
for (k, d, s), n in g.items(): pairs[k].append((n, d, s))
for k in sorted(pairs, key=lambda k: (k.split("_",1)[1] if "_" in k else k, k)):
    tot = sum(n for n, _, _ in pairs[k])
    print(f"{k} {tot}")
    for n, d, s in sorted(pairs[k], reverse=True)[:4]:
        print(f"    {n:5d} {d[:110]} -> {', '.join(s)[:110]}")
