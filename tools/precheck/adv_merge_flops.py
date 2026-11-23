#!/usr/bin/env python3
"""merge_flops.py OUT.json IN.json ... -- merge per-host harvest_flops.py caches (newest kit per type wins per section)"""
import json, sys, time
out = dict(schema="precheck-r2.flops_cache.v1", made=time.strftime("%Y-%m-%d %H:%M"), hosts=[], flops={}, placed={}, placed_bins={})
for f in sys.argv[2:]:
    d = json.load(open(f))
    out["hosts"].append(d.get("host"))
    for sec in ("flops", "placed", "placed_bins"):
        for tn, r in (d.get(sec) or {}).items():
            if tn not in out[sec] or r["ts"] > out[sec][tn]["ts"]:
                out[sec][tn] = r
json.dump(out, open(sys.argv[1], "w"))
print("MERGED", {k: len(out[k]) for k in ("flops", "placed", "placed_bins")})
