"""Spine placement review: render groups + hop lines + taps, measure hops/pin->reg/stations/density/taps."""
import sys, re, json, math, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
d, n = sys.argv[1], sys.argv[2]
W = H = 0; I = {}; P = {}; PR = []; RR = []
for ln in open(f"{d}/{n}.place.tsv"):
    p = ln.rstrip("\n").split("\t")
    if p[0] == "DIE": W, H = float(p[1]), float(p[2])
    elif p[0] == "I": I[p[1]] = (p[2], *map(float, p[3:7]))
    elif p[0] == "P": P[p[1]] = (p[2], float(p[3]), float(p[4]))
    elif p[0] == "PR": PR.append((p[1], p[2], float(p[3]), float(p[4]), p[5], float(p[6]), float(p[7]), float(p[8]), p[9] if len(p) > 9 else ""))
    elif p[0] == "RR": RR.append((p[1], float(p[2]), float(p[3]), p[4], float(p[5]), float(p[6]), float(p[7])))
tag = {}
for ln in open(f"{d}/ot_face_flops.txt"):
    p = ln.rstrip("\n").split("\t")
    tag[p[0]] = p[1]
def grp(name, m):
    t = tag.get(name)
    if "DFF" in m:
        if t is None: return "logic_ff"
        if t in "NSEW": return "pin_reg"
        if t.startswith("st"): return "ft_station"
        if t.startswith("ist"): return "int_station"
        if t.startswith(("rrl", "rentry")): return "reset"
        return "logic_ff"
    if m.startswith(("BUF", "HB")): return "buf"
    if m.startswith("INV"): return "buf"
    return "comb"
G = collections.defaultdict(list); area = 0.0
for nm, (m, x0, y0, x1, y1) in I.items():
    g = grp(nm, m); G[g].append(((x0 + x1) / 2, (y0 + y1) / 2)); area += (x1 - x0) * (y1 - y0)
ntag_unmatched = sum(1 for k in tag if k not in I)
res = {"type": n, "outline_um": [W, H], "cells": len(I), "groups": {k: len(v) for k, v in G.items()},
       "util": round(area / (W * H), 4), "face_flop_tags_not_found_in_odb": ntag_unmatched}
# density 50 um bins
B = 50; nx, ny = int(math.ceil(W / B)), int(math.ceil(H / B)); den = [[0.0] * ny for _ in range(nx)]
for nm, (m, x0, y0, x1, y1) in I.items():
    den[min(nx - 1, int((x0 + x1) / 2 / B))][min(ny - 1, int((y0 + y1) / 2 / B))] += (x1 - x0) * (y1 - y0) / (B * B)
flat = sorted(v for c in den for v in c)
res["density_50um"] = {"max": round(flat[-1], 3), "p99": round(flat[int(.99 * (len(flat) - 1))], 3), "bins_gt_0.7": sum(v > .7 for v in flat), "empty_bins_frac": round(sum(v < .005 for v in flat) / len(flat), 3)}
# hops
rr = sorted(RR, key=lambda r: -r[6])
res["reg_reg"] = {"n": len(RR), "max": round(rr[0][6], 1) if rr else None, "gt405": sum(r[6] > 405 for r in RR), "gt345": sum(r[6] > 345 for r in RR),
                  "worst": [[r[0], r[3], round(r[6], 1)] for r in rr[:8]]}
def gcls(name):
    t = tag.get(name, ""); return t.split(":")[0] if t else "logic"
cls = collections.defaultdict(float)
for r in RR: k = gcls(r[0]) + "->" + gcls(r[3]); cls[k] = max(cls[k], r[6])
res["reg_reg_max_by_class"] = {k: round(v, 1) for k, v in sorted(cls.items(), key=lambda x: -x[1])[:15]}
# pin -> reg by face (skip clock taps)
pf = collections.defaultdict(list); nofl = []
for nm, io, px, py, ff, fx, fy, dist, why in PR:
    if re.match(r"clk(_t\d+)?$", nm): continue
    face = "W" if px < 1 else "E" if px > W - 1 else "S" if py < 1 else "N" if py > H - 1 else "I"
    if dist < 0: nofl.append([nm, why]); continue
    pf[(face, io)].append((dist, nm))
res["pin_reg"] = {f"{f}/{io}": {"n": len(v), "max": round(max(v)[0], 1), "p90": round(sorted(v)[int(.9 * (len(v) - 1))][0], 1), "worst": max(v)[1]} for (f, io), v in sorted(pf.items())}
res["pins_without_reg"] = nofl[:20]; res["pins_without_reg_n"] = len(nofl)
# face pin density (pins / um along face, 50 um windows)
fd = {}
for f in "NSEW":
    pos = [(v[1] if f in "NS" else v[2]) for k, v in P.items() if (f == "W" and v[1] < 1) or (f == "E" and v[1] > W - 1) or (f == "S" and v[2] < 1) or (f == "N" and v[2] > H - 1)]
    L = W if f in "NS" else H; c = collections.Counter(int(x // 50) for x in pos)
    fd[f] = {"pins": len(pos), "max_per_um_50win": round(max(c.values()) / 50, 2) if c else 0, "span": [round(min(pos), 1), round(max(pos), 1)] if pos else None}
res["face_pins"] = fd
# ft stations: per slot/bit, positions in order, deviation from straight line in->out
ch = collections.defaultdict(dict)
for nm, (m, x0, y0, x1, y1) in I.items():
    mm = re.match(r"u_ft_(\w+?)_s(\d+)/q\\?\[(\d+)\\?\]", nm)
    if mm and "DFF" in m: ch[(mm.group(1), int(mm.group(3)))][int(mm.group(2))] = ((x0 + x1) / 2, (y0 + y1) / 2)
dev = collections.defaultdict(float); lat = collections.defaultdict(float)
for (s, b), st in ch.items():
    xs = [st[k][0] for k in sorted(st)]
    dev[s] = max(dev[s], max(xs) - min(xs))
res["ft_slot_lateral_spread_um"] = {k: round(v, 1) for k, v in dev.items()}
res["ft_slot_stations"] = {s: max(len(st) for (ss, b), st in ch.items() if ss == s) for s in dev}
# internal stations planned vs actual
ist = {}
for ln in open(f"{d}/istations.tcl"):
    mm = re.match(r"is_place \{\*(u_ist_\w+?_\d+)\[\./\]\*\} ([\d.]+) ([\d.]+)", ln)
    if mm: ist[mm.group(1)] = (float(mm.group(2)), float(mm.group(3)))
idev = {}
for k, (x, y) in ist.items():
    pts = [((v[1] + v[3]) / 2, (v[2] + v[4]) / 2) for nm, v in I.items() if nm.startswith(k + "/") and "DFF" in v[0]]
    if pts:
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        idev[k] = {"bits": len(pts), "planned": [x, y], "centroid": [round(cx, 1), round(cy, 1)], "max_from_plan": round(max(abs(p[0] - x) + abs(p[1] - y) for p in pts), 1)}
res["int_stations"] = idev
# clock taps: nearest tap per flop
taps = {k: (v[1], v[2]) for k, v in P.items() if re.match(r"clk(_t\d+)?$", k)}
tc = collections.Counter(); trad = collections.defaultdict(float)
for nm, (m, x0, y0, x1, y1) in I.items():
    if "DFF" not in m: continue
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    t = min(taps, key=lambda k: abs(taps[k][0] - cx) + abs(taps[k][1] - cy)); tc[t] += 1
    trad[t] = max(trad[t], abs(taps[t][0] - cx) + abs(taps[t][1] - cy))
res["clock_taps"] = {"n": len(taps), "sinks_max": max(tc.values()), "sinks_min_loaded": min(tc.values()), "zero_sink_taps": sorted(set(taps) - set(tc)),
                     "over_1500": [k for k, v in tc.items() if v > 1500], "leaf_radius_max_um": round(max(trad.values()), 1), "per_tap": dict(sorted(tc.items()))}
json.dump(res, open(f"{d}/{n}.review.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("int_stations",)}, indent=1)[:6000])
print("int_stations", {k: (v["bits"], v["max_from_plan"]) for k, v in idev.items()})
# render
fig, ax = plt.subplots(figsize=(11, 11 * H / W))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1))
sty = [("comb", "0.85", .2), ("buf", "0.45", .3), ("logic_ff", "purple", .6), ("pin_reg", "g", 1.0), ("ft_station", "orange", 1.2), ("int_station", "c", 1.2), ("reset", "r", 6)]
for k, c, s in sty:
    if G[k]: ax.scatter(*zip(*G[k]), s=s, c=c, label=f"{k} {len(G[k])}", linewidths=0, rasterized=True)
segs = [((r[1], r[2]), (r[4], r[5])) for r in RR if r[6] > 150]
ax.add_collection(LineCollection(segs, colors=[("r" if s > 0 else "b") for s in [0] * len(segs)], linewidths=.15, alpha=.25))
long = [((r[1], r[2]), (r[4], r[5])) for r in RR if r[6] > 405]
if long: ax.add_collection(LineCollection(long, colors="r", linewidths=1.2))
ps = [(v[1], v[2]) for v in P.values()]
ax.scatter(*zip(*ps), s=.4, c="b", label=f"pins {len(ps)}")
ax.scatter([t[0] for t in taps.values()], [t[1] for t in taps.values()], marker="x", s=40, c="k", label=f"clk taps {len(taps)} (max sinks {res['clock_taps']['sinks_max']})")
for t, (x, y) in taps.items(): ax.annotate(str(tc.get(t, 0)), (x, y), fontsize=6, xytext=(3, 3), textcoords="offset points")
for k, (x, y) in ist.items(): ax.scatter([x], [y], marker="+", s=30, c="teal")
ax.set_xlim(-10, W + 10); ax.set_ylim(-10, H + 10); ax.set_aspect("equal"); ax.legend(loc="upper left", fontsize=6, markerscale=3, bbox_to_anchor=(1.01, 1))
rr_ = res["reg_reg"]
ax.set_title(f"{n} 3_place {W}x{H} um  cells {len(I)} util {res['util']}  reg->reg max {rr_['max']} (>405: {rr_['gt405']})  lines = hops >150 um, thick red >405; + = planned int stations", fontsize=7)
fig.savefig(f"{d}/{n}.place.png", dpi=150, bbox_inches="tight")
