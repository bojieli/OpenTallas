#!/usr/bin/env python3
"""DIE-HBM-63/CUTS part 8: replicas of one master keep one pin list. Bits a replica leaves open (the status outputs only column 0
drives into the head) stay on the master as free pins, top=[] peer=[]."""
import json, sys
f = sys.argv[1]; C = json.load(open(f)); U = {}
for s in C["subs"]:
    U.setdefault(s["module"], {}).update({k: 1 for k in s["bits"]})
n = 0
for s in C["subs"]:
    for k in U[s["module"]]:
        if k not in s["bits"]:
            s["bits"][k] = dict(top=[], peer=[]); n += 1
json.dump(C, open(f, "w")); print("open replica bits added", n)
