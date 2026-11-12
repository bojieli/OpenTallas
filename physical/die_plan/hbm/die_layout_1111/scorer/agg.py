#!/usr/bin/env python3
"""aggregate trace_readers.py lines by (cores, centroid)"""
import json
import sys

agg = {}
for ln in sys.stdin:
    try:
        o = json.loads(ln)
    except Exception:
        print(ln[:300])
        continue
    k = (tuple(o["cores"]), tuple(o["centroid"]) if o["centroid"] else None, o["depth"])
    a = agg.setdefault(k, [0, [], 0, []])
    a[0] += o["nbits"]
    a[1] += o["runs"][:2]
    a[2] += 1
    a[3].append(o["sig"])
for k, v in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(v[0], "bits", v[2], "sigs", "cores", list(k[0]), "centroid", k[1], "depth", k[2], "runs", v[1][:4], "eg", v[3][:2])
