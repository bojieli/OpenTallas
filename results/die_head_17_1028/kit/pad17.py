#!/usr/bin/env python3
"""DIE-HEAD-17: per-tap BUFx4 pad counts from ROUTED (GRT-RC) tap means of a measured pass.
pad_new = max(0, pad_now + round((T - routed_mean)/B4)). args: meas assign plan.json T B4 out.json"""
import sys, json, statistics as st, collections
meas, asg, plan, T, B4, out = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3])), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
a = {}
for l in open(asg):
    n, k = l.split(); a[n.replace("\\", "")] = int(k)
per = collections.defaultdict(list)
for l in open(meas):
    f = l.split()
    if f[0] != "CK": continue
    i = f[1].rsplit("/", 1)[0].replace("\\", "")
    if i in a: per[a[i]].append(float(f[2]))
pads = {}
for t in plan["taps"]:
    m = st.mean(per[t["id"]]); p0 = t.get("pad", 0)
    pads[str(t["id"])] = max(0, p0 + round((T - m) / B4))
    print(f"tap {t['id']:2d} {t['node']:4s} routed mean {m:6.1f} pad {p0:2d} -> {pads[str(t['id'])]:2d}  predicted {m + (pads[str(t['id'])]-p0)*B4:6.1f}")
json.dump(pads, open(out, "w"), indent=0)
print("total pads", sum(pads.values()))
