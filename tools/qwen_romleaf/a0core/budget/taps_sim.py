#!/usr/bin/env python3
"""QC a0v8: emulate tools/die_plan/clock_taps.tcl on estimated sink sites: nearest tap (Manhattan), then cap
OT_TAP_MAX_SINKS (1500) with re-assignment of the cheapest sinks (extra distance <= OT_TAP_PITCH_UM/2 = 120 um)."""
import json, pickle, sys, collections
sinks = pickle.load(open(sys.argv[1], 'rb'))
taps = json.load(open(sys.argv[2]))["taps"]
CAP, MAXX = 1500, 120.0
T = [(t["name"], t["xy"][0], t["xy"][1]) for t in taps]
def d(s, t): return abs(s[0] - t[1]) + abs(s[1] - t[2])
by = collections.defaultdict(list)
for n, xy in sinks:
    best = min(T, key=lambda t: d(xy, t)); by[best[0]].append(xy)
stuck = set(); moves = 0
for _ in range(8 * len(T)):
    over = next((t for t in T if t[0] not in stuck and len(by[t[0]]) > CAP), None)
    if not over: break
    ex = len(by[over[0]]) - CAP
    cand = []
    for i, s in enumerate(by[over[0]]):
        d0 = d(s, over); bt = None; bd = 0
        for t in T:
            if t[0] == over[0] or len(by[t[0]]) >= CAP: continue
            dd = d(s, t) - d0
            if bt is None or dd < bd: bt, bd = t, dd
        if bt is not None and bd <= MAXX: cand.append((bd, i, bt))
    if not cand: stuck.add(over[0]); continue
    cand.sort(key=lambda c: c[0]); tn = cand[0][2]
    room = CAP - len(by[tn[0]]); take = [c for c in cand if c[2][0] == tn[0]][:min(ex, room)]
    idx = set(c[1] for c in take)
    by[tn[0]].extend(by[over[0]][i] for i in idx)
    by[over[0]] = [s for i, s in enumerate(by[over[0]]) if i not in idx]; moves += len(idx)
rep = {}
for t in T:
    l = by[t[0]]
    reach = max((d(s, t) for s in l), default=0)
    rep[t[0]] = dict(xy=[t[1], t[2]], sinks=len(l), reach_um=round(reach, 1))
print("sinks", len(sinks), "moves", moves, "stuck(>cap)", sorted(stuck))
print("over cap:", {k: v["sinks"] for k, v in rep.items() if v["sinks"] > CAP})
print("empty:", [k for k, v in rep.items() if v["sinks"] == 0])
print("reach>180:", {k: v["reach_um"] for k, v in rep.items() if v["reach_um"] > 180})
for k, v in rep.items(): print("  ", k, v)
if len(sys.argv) > 3: json.dump(rep, open(sys.argv[3], "w"), indent=1)
