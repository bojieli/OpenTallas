#!/usr/bin/env python3
"""G0 error diff keyed without the macro instance name in the message ("(stage N, bit 0, macro pvgX_pY)"), because a pv
pair swap renames the macro of the same slot error. usage: g0_slot.py BASE_G0_DIR NEW_G0_DIR"""
import json, glob, re, sys, collections
def errs(d):
    r = json.load(open(glob.glob(d + "/**/g0_report.json", recursive=True)[0]))
    return collections.Counter(x.get("check", "") + " | " + re.sub(r"\(stage.*", "", x.get("msg", x.get("message", "")))
                               for x in r.get("findings") or [] if (x.get("level") or x.get("severity")) == "ERROR")
a, b = errs(sys.argv[1]), errs(sys.argv[2])
print(f"G0 slot-keyed errors base {sum(a.values())} -> {sum(b.values())}; NEW {sum((b-a).values())}; GONE {sum((a-b).values())}")
for k in (b - a): print("  NEW:", k[:300])
