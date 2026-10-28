#!/usr/bin/env python3
"""Merge per-module C18 generation results from the gen logs (drivers ran in 5 pieces) + preflight receipts.
  merge_gen.py KITDIR PREFLIGHTDIR OUT.json"""
import json, sys, glob, os, re
kd, pd, out = sys.argv[1:4]
res = {}
for log in sorted(glob.glob(f"{kd}/gen_*_c18*.log")):
    m = re.sub(r"_c18(_[0-9a-f]{6})?\.log$", "", os.path.basename(log)[4:])
    lines = open(log).read().strip().splitlines()
    tail = lines[-1] if lines else ""
    kit = None
    try:
        kit = json.loads(tail).get("kit")
    except ValueError:
        pass
    cls = "OK" if kit else next((c for c in ("NO_RECIPE", "PORT_MISMATCH", "MAP_AMBIGUOUS", "MACRO_PLACEMENT", "off the plan lattice")
                                 if c in tail), "GEN_FAIL")
    pf = None
    if kit:
        r = f"{pd}/{os.path.basename(kit)}.json"
        if os.path.isfile(r):
            d = json.load(open(r)); pf = dict(verdict=d["verdict"], issues=d["issues"])
    res.setdefault(m, []).append(dict(cls=cls, kit=kit, log=log, msg=tail[:400] if not kit else "", preflight=pf))
json.dump(res, open(out, "w"), indent=1)
for m, v in sorted(res.items()):
    print(m, [(x["cls"], (x["preflight"] or {}).get("verdict"), len((x["preflight"] or {}).get("issues", []))) for x in v])
