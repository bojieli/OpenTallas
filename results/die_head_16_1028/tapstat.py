#!/usr/bin/env python3
"""Per-tap register clock arrivals from meas14 output (TT/FF .meas) + pass-2 pad plan. args: meas assign16 plan16.json [T] [buf4_ps] [padout]"""
import sys, json, statistics as st, collections
meas, asg, plan = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
T = float(sys.argv[4]) if len(sys.argv) > 4 else 450.0
B4 = float(sys.argv[5]) if len(sys.argv) > 5 else 22.0
a = {}
for l in open(asg):
    n, k = l.split(); a[n.replace("\\", "")] = int(k)
per = collections.defaultdict(list); allv = []; slews = []; cores = []; miss = 0
for l in open(meas):
    f = l.split()
    if f[0] == "CORE": cores.append(l.strip()); continue
    if f[0] != "CK": continue
    inst = f[1].rsplit("/", 1)[0].replace("\\", "")
    v = float(f[2]); slews.append(max(float(f[6]), float(f[7])))
    if inst in a: per[a[inst]].append(v); allv.append(v)
    else: miss += 1
allv.sort()
q = lambda p: allv[min(len(allv) - 1, int(p * len(allv)))]
print(f"regs {len(allv)} (not on a tap {miss}) insertion min {allv[0]:.1f} p50 {q(.5):.1f} p99 {q(.99):.1f} max {allv[-1]:.1f}  max CK slew {max(slews):.1f}")
pads = {}
for t in plan["taps"]:
    v = per.get(t["id"], [])
    if not v: print(f"tap {t['id']} NO MEAS"); continue
    m = st.mean(v); pads[str(t["id"])] = max(0, round((T - m) / B4)) + t.get("pad", 0)
    print(f"tap {t['id']:2d} {t['node']:4s} n {len(v):5d} mean {m:6.1f} min {min(v):6.1f} max {max(v):6.1f} spread {max(v)-min(v):5.1f} model {t['model_ps']:6.1f} pad_now {t.get('pad',0)} -> pad {pads[str(t['id'])]}")
for c in cores: print(c)
if len(sys.argv) > 6: json.dump(pads, open(sys.argv[6], "w"), indent=0)
