#!/usr/bin/env python3
"""total RCX cap, coupling cap and total R per ot_ms_* net from 6_final.spef (pre-hold); joins via_census.json."""
import sys, json, re
kit = sys.argv[1]
nm = {}; nets = {}; cur = None; sec = None
for l in open(f"{kit}/6_final.spef"):
    if l.startswith("*NAME_MAP"): sec = "map"; continue
    if sec == "map":
        if l.startswith("*") and l[1].isdigit():
            k, v = l.split(None, 1); nm[k] = v.strip(); continue
        elif l.strip() == "": continue
        else: sec = None
    if l.startswith("*D_NET"):
        f = l.split(); n = nm.get(f[1], f[1])
        cur = n if n.startswith("ot_ms_") else None
        if cur: nets[cur] = dict(ctot=float(f[2]), cc=0.0, cg=0.0, r=0.0)
        sec = None; continue
    if cur is None: continue
    if l.startswith("*CAP"): sec = "cap"; continue
    if l.startswith("*RES"): sec = "res"; continue
    if l.startswith("*END"): cur = None; continue
    f = l.split()
    if sec == "cap" and len(f) == 4: nets[cur]["cc"] += float(f[3])
    elif sec == "cap" and len(f) == 3: nets[cur]["cg"] += float(f[2])
    elif sec == "res" and len(f) == 4: nets[cur]["r"] += float(f[3])
vc = json.load(open(f"{kit}/via_census.json"))
seen = set()
print("%-16s %6s %5s %7s %7s %6s %7s %7s" % ("net", "len", "vias", "Ctot", "Ccoup", "C/um", "Rtot", "d_stage"))
for x in sorted(vc, key=lambda x: -x["d_stage"]):
    if x["net"] in seen: continue
    seen.add(x["net"]); s = nets.get(x["net"])
    if not s or x["len_um"] < 20: continue
    x.update(spef=s)
    print("%-16s %6.1f %5d %7.2f %7.2f %6.3f %7.1f %+7.2f" % (x["net"][6:], x["len_um"], x["vias"], 1e3*s["ctot"], 1e3*s["cc"], 1e3*s["ctot"] / x["len_um"], s["r"], x["d_stage"]))
json.dump(vc, open(f"{kit}/via_census.json", "w"), indent=1)
