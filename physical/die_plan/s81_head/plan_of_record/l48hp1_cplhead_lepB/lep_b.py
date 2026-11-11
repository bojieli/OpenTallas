#!/usr/bin/env python3
"""CPL-HEAD 11-11: hd_lep0N proposal B (+129.6 um width, W side) as a plan event on l48hp1.
  die:   nst4 (hd_st_n4, single instance) E edge cropped 1123.2 -> 993.6; lep0N origin x 6998.4 -> 6868.8,
         outline 1762.56 -> 1892.16 (E edge 8760.96 unchanged, so ctl / spine untouched); the two nst4-crop die
         channels are clipped to x <= 6868.8.
  lep0N: piecewise x map (old type-local x -> new): W region [0, 846.72) +0; centre gap [846.72, 881.28) +43.2;
         E pairs / E half street [881.28, 1658.88) +86.4; E strip [1658.88, W] +129.6; N-face items (window,
         band, edge tap, collector, pins at y >= 1160 inside a N window span) +129.6 so every port keeps its global
         position.  Hard cores move by the map of their origin (positions only, orients unchanged).
  nst4:  x of every point/rect scaled by 993.6/1123.2 (4 ft stations per chain kept: 280.8 -> 248.4 um pitch).
usage: lep_b.py IN.json OUT.json
"""
import copy, json, re, sys

DX = 129.6
OLDW, NEWW = 1762.56, 1762.56 + DX
N4W0, N4W1 = 1123.2, 1123.2 - DX
P = json.load(open(sys.argv[1]))
Q = copy.deepcopy(P)
T = Q["partition_types"]
t = T["hd_lep0N"]
H = t["outline_um"][1]
nwin = [b["window_um"] for b in t["buses"] if b["face"] == "N"]


def f(x):
    if x < 846.72 - 1e-6:
        return x
    if x < 881.28 - 1e-6:
        return x + 43.2
    if x < 1658.88 - 1e-6:
        return x + 86.4
    return x + DX


def is_n(x, y):
    return y >= 1160 and any(w0 - 30 <= x <= w1 + 30 for w0, w1 in nwin)


def mp(x, y):
    return x + DX if is_n(x, y) else f(x)


log = []
# buses: N face windows +DX (global fixed), others y-based
for b in t["buses"]:
    if b["face"] in "NS":
        b["window_um"] = [round(v + DX, 4) for v in b["window_um"]]
        if b["face"] == "S":
            raise SystemExit("unexpected S bus")
def lmap(x, y):
    if x > OLDW - 8.7:
        return x + DX
    return mp(x, y)


def lwalk(o, path):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("insertion_ps", "insertion_ff_ps", "tap_radius_um", "reach_um"):
                continue
            lwalk(v, path + "." + k)
    elif isinstance(o, list):
        if o and all(isinstance(v, (int, float)) for v in o) and ("_um" in path or path.endswith("xy") or "sites" in path):
            if ("rect" in path or "islands" in path) and len(o) == 4:
                d = lmap(o[0], o[3]) - o[0]
                if o[3] > 1100 and any(w0 - 30 <= o[0] <= w1 + 30 for w0, w1 in nwin):
                    d = DX
                o[0] = round(o[0] + d, 4); o[2] = round(o[2] + d, 4)
            elif len(o) >= 2:
                o[0] = round(lmap(o[0], o[1]), 4)
        else:
            for i, v in enumerate(o):
                lwalk(v, path + "[%d]" % i)


for k in ("clock", "reset", "count_straps", "reset_start_raw_exports"):
    if k in t:
        lwalk(t[k], k)
old = {}
for h in t["hard_cores"]:
    x, y = h["origin_um"]
    old[h["inst"]] = (x, y)
    h["origin_um"] = [round(f(x), 4), y]
t["outline_um"] = [round(NEWW, 4), H]
t["note"] = (t.get("note") or "") + " | CPL-HEAD 11-11 REDESIGN B: +129.6 um W (nst4 E crop), piecewise x map (W +0, gap +43.2, E +86.4, E strip +129.6, N windows fixed globally)"
# sink bins asset: left as is (re-derived by the die owner's clock step) -> reported
# ---- nst4
n4 = T["hd_st_n4"]
s = N4W1 / N4W0


def sx(x):
    return round(x * s, 4)


n4["outline_um"] = [round(N4W1, 4), n4["outline_um"][1]]
c4 = n4["clock"]


def n4x(x):
    return round(x - DX, 4) if x > N4W0 - 8.7 else sx(x)


def n4walk(o, path):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("insertion_ps", "insertion_ff_ps", "tap_radius_um", "reach_um"):
                continue
            n4walk(v, path + "." + k)
    elif isinstance(o, list):
        if o and all(isinstance(v, (int, float)) for v in o) and ("_um" in path or path.endswith("xy") or "sites" in path):
            if ("rect" in path or "islands" in path) and len(o) == 4:
                d = n4x(o[0]) - o[0] if o[2] <= N4W0 - 8.7 else -DX
                o[0] = round(o[0] + d, 4); o[2] = round(o[2] + d, 4)
            elif len(o) >= 2:
                o[0] = n4x(o[0])
        else:
            for i, v in enumerate(o):
                n4walk(v, path + "[%d]" % i)


for k in ("clock", "reset", "count_straps", "reset_start_raw_exports"):
    if k in n4:
        n4walk(n4[k], k)
n4["note"] = (n4.get("note") or "") + " | CPL-HEAD 11-11 REDESIGN B: E edge cropped 1123.2 -> 993.6 (lep0N +129.6 W); 4 ft stations per chain kept (248.4 um pitch)"
# ---- die
for p in Q["partitions"]:
    if p["name"] == "lep0N":
        p["origin_um"] = [round(p["origin_um"][0] - DX, 4), p["origin_um"][1]]
for c in Q["die"]["channels"]:
    r = c["rect_um"]
    if abs(r[0] - 5875.2) < 0.01 and abs(r[2] - 7318.08) < 0.01:
        c["rect_um"] = [r[0], r[1], 6998.4 - DX, r[3]]
json.dump(Q, open(sys.argv[2], "w"), indent=1)
# report leftovers: any lep0N / nst4 numeric pair outside the new outline
def scan(o, W_, path, out):
    if isinstance(o, dict):
        for k, v in o.items():
            scan(v, W_, path + "." + k, out)
    elif isinstance(o, list):
        if len(o) >= 2 and all(isinstance(v, (int, float)) for v in o[:2]) and ("_um" in path or path.endswith("xy")):
            if not any(k in path for k in ("outline_um", "track_offset", "window_um", "insertion")) and (o[0] > W_ + 0.01 or o[0] < -0.01):
                out.append((path, o))
        else:
            for i, v in enumerate(o):
                scan(v, W_, path + "[%d]" % i, out)
for tn, W_ in (("hd_lep0N", NEWW), ("hd_st_n4", N4W1)):
    out = []
    scan(T[tn], W_, tn, out)
    print(tn, "points outside outline:", len(out), out[:6])
print("wrote", sys.argv[2])
