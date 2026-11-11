#!/usr/bin/env python3
import json, glob, sys, collections
def errs(d):
    r = json.load(open(glob.glob(d + "/**/g0_report.json", recursive=True)[0]))
    return collections.Counter(x.get("check", "") + " | " + x.get("msg", x.get("message", "")) for x in r.get("findings") or []
                               if (x.get("level") or x.get("severity")) == "ERROR")
a, b = errs(sys.argv[1]), errs(sys.argv[2])
print(f"G0 errors base {sum(a.values())} -> {sum(b.values())}; NEW {sum((b-a).values())}; GONE {sum((a-b).values())}")
for k in (b - a): print("  NEW:", k[:300])
