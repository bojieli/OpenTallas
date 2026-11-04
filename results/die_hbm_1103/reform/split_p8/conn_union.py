#!/usr/bin/env python3
"""DIE-HBM-63/CUTS part 8: every sub keeps its full RTL pin list. Bits a sub leaves open (the status outputs only column 0
drives into the head) stay on the master as free pins, top=[] peer=[]."""
import json, sys
f = sys.argv[1]; C = json.load(open(f)); n = 0
for s in C["subs"]:
    for p, d in s["ports"].items():
        for k in ([p] if d["width"] == 1 else [f"{p}[{i}]" for i in range(d["width"])]):
            if k not in s["bits"]:
                s["bits"][k] = dict(top=[], peer=[]); n += 1
json.dump(C, open(f, "w")); print("open bits added", n)
