#!/usr/bin/env python3
"""receipt.py STAGE IN.json OUT.json RECEIPT.json [k=v ...]: stage receipt (shas, changed types / top-level keys)."""
import hashlib
import json
import sys

stage, fi, fo, fr = sys.argv[1:5]
extra = dict(x.split("=", 1) for x in sys.argv[5:])
ri, ro = open(fi, "rb").read(), open(fo, "rb").read()
A, B = json.loads(ri), json.loads(ro)
ta, tb = A["partition_types"], B["partition_types"]
changed = sorted(t for t in set(ta) | set(tb) if ta.get(t) != tb.get(t))
top = sorted(k for k in set(A) | set(B) if k != "partition_types" and A.get(k) != B.get(k))
rec = dict(stage=stage, in_file=fi, in_sha256=hashlib.sha256(ri).hexdigest(), out_file=fo,
           out_sha256=hashlib.sha256(ro).hexdigest(), types_changed=changed, n_types_changed=len(changed),
           top_level_changed=top, **extra)
json.dump(rec, open(fr, "w"), indent=1)
print(stage, "in", rec["in_sha256"][:12], "out", rec["out_sha256"][:12], "types", len(changed), "top", top)
