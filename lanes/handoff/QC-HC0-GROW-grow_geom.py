"""QC-HC0-GROW geometry draft: usage grow_geom.py BASE.json OUT.json REPORT.json
Grows the E-strip hc row (hc0..hc3 types) by DY at the N edge (S/E faces fixed, bottom-aligned), shifts the 48 E cores,
grows the die, moves N-anchored items of the grown types.  No station/tap/bin re-derivation here (see report 'todo')."""
import json, sys, copy, math, hashlib, re
DY = 864.0
base, out, rep = sys.argv[1:4]
raw = open(base, "rb").read(); old = json.loads(raw); new = copy.deepcopy(old)
pt = new["partition_types"]; P = new["partitions"]
isnum = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
types = sorted({q["type"] for q in P if re.match(r"sl_E\d_hc\d$", q["name"])})
shared = sorted({q["type"] for q in P if q["name"].startswith("sl_W") and q["type"] in types})
CLONE = {}
for q in P:
    if re.match(r"sl_E\d_hc\d$", q["name"]) and q["type"] in shared:
        nn = q["type"] + "__g864"
        if nn not in pt:
            pt[nn] = copy.deepcopy(pt[q["type"]]); pt[nn]["module"] = pt[nn]["module"]; CLONE[q["type"]] = nn
        q["type"] = nn
types = sorted({q["type"] for q in P if re.match(r"sl_E\d_hc\d$", q["name"])})
r = dict(clones=CLONE, dy=DY, types=types, shared_with_W=shared, moved={}, hop_over=[], added=[], lifted=[])
def mv(o, thr, cnt):
    if isinstance(o, list) and len(o) == 2 and all(isnum(v) for v in o) and o[1] > thr:
        o[1] = round(o[1] + DY, 6); cnt[0] += 1
    elif isinstance(o, list) and len(o) == 4 and all(isnum(v) for v in o) and o[2] > o[0] and o[3] > thr:
        o[3] = round(o[3] + DY, 6)
        if o[1] > thr: o[1] = round(o[1] + DY, 6)
        cnt[0] += 1

LIM = 405.0
def man(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
def resample(poly, n):
    """n points at arclength k*L/n (k=0..n-1) along poly (Manhattan length), L=total; returns pts, L"""
    L = sum(man(a, b) for a, b in zip(poly, poly[1:])); out = []
    for k in range(n):
        tgt = k * L / n; acc = 0.0
        for a, b in zip(poly, poly[1:]):
            d = man(a, b)
            if acc + d >= tgt - 1e-9 or b is poly[-1]:
                f = 0 if d == 0 else min(1.0, max(0.0, (tgt - acc) / d)); out.append([round(a[0]+(b[0]-a[0])*f, 3), round(a[1]+(b[1]-a[1])*f, 3)]); break
            acc += d
    return out, L
def respace(poly_fixed_end_in, regs_n, tail):
    pass
for tn in types:
    t = pt[tn]; H0 = t["outline_um"][1]; thr = H0 - 60; cnt = [0]
    t["outline_um"][1] = round(H0 + DY, 6)
    lc = t["clock"].get("landing_contract", {})
    for p in lc.get("pins", []): mv(p["xy_um"], thr, cnt)
    for b in lc.get("bands", {}).values(): mv(b["rect_um"], thr, cnt)
    for s in lc.get("collector_local_sources", []):
        mv(s.get("xy_um"), thr, cnt); mv(s.get("pin_xy_um"), thr, cnt); 
        if s.get("band"): mv(s["band"]["rect_um"], thr, cnt)
    for e in t["clock"].get("edge_clocks", []): mv(e["tap_um"], thr, cnt)
    for s in t.get("ft_slots", []):
        for rg in s.get("regs_um",[])[:1]: mv(rg, thr, cnt)       # pin-side station only
    for s in t.get("internal_stations", []):
        mv(s.get("to_um"), thr, cnt)
        for rg in s.get("regs_um", [])[-1:]:
            if rg[1] > thr: mv(rg, thr, cnt)
    r["moved"][tn] = cnt[0]
    # re-space the stretched station paths (counts kept unless a hop would exceed LIM)
    for s in t.get("ft_slots", []):
        rg = s.get("regs_um", [])
        if not rg or rg[0][1] < H0: continue
        ow = s.get("out_window_um"); face = s.get("out_face")
        outp = [t["outline_um"][0], (ow[0]+ow[1])/2] if face == "E" else None
        if outp is None: r["hop_over"].append((tn, "ft:" + s["name"], "OUT_FACE_" + str(face))); continue
        poly = [rg[0]] + rg[1:] + [outp]; n = len(rg)
        L = sum(man(a, b) for a, b in zip(poly, poly[1:])); nn = max(n, math.ceil(L / LIM))
        pts, _ = resample(poly, nn); 
        if nn != n: r["added"].append((tn, "ft:" + s["name"], n, nn))
        s["regs_um"] = pts; s["stations"] = nn if "stations" in s else s.get("stations")
        if "stations" in s and s["stations"] is None: del s["stations"]
    for s in t.get("internal_stations", []):
        if s["to_um"][1] < H0: continue
        n = len(s["regs_um"]); poly = [s["from_um"], s["to_um"]]
        L = man(*poly); nn = max(n, math.ceil(L / LIM) - 1)
        if nn > n and L - (n + 1) * LIM <= 60:      # launch estimate sits low in the type: lift it by the excess instead of adding a cycle
            lift = math.ceil(L - (n + 1) * LIM) + 1; 
            if s.get("leaf_um") == s["from_um"]: s["leaf_um"] = [s["leaf_um"][0], round(s["leaf_um"][1] + lift, 6)]
            s["from_um"] = [s["from_um"][0], round(s["from_um"][1] + lift, 6)]; r["lifted"].append((tn, s["conn"], lift))
            poly = [s["from_um"], s["to_um"]]; L = man(*poly); nn = n
        pts, _ = resample(poly, nn + 1); pts = pts[1:]
        if nn != n: r["added"].append((tn, "int:" + s["conn"], n, nn))
        s["regs_um"] = pts
    for s in t.get("ft_slots", []):
        rg = s.get("regs_um", [])
        for a, b in zip(rg, rg[1:]):
            if man(a, b) > LIM: r["hop_over"].append((tn, "ft:" + s["name"], round(man(a, b))))
    for s in t.get("internal_stations", []):
        pts = [s["from_um"]] + s["regs_um"] + [s["to_um"]]
        for a, b in zip(pts, pts[1:]):
            if man(a, b) > LIM: r["hop_over"].append((tn, "int:" + s["conn"], round(man(a, b))))
# partitions
y_cut = 15465.6 - 0.01
sh = 0
for q in P:
    if q["origin_um"][0] >= 16380 and q["origin_um"][1] >= y_cut:
        q["origin_um"][1] = round(q["origin_um"][1] + DY, 6); sh += 1
r["partitions_shifted"] = sh
d = new["die"]; H0 = d["outline_um"][1]; d["outline_um"][1] = round(H0 + DY, 6)
for f in d["pg"]["bumps"]["fields"]:
    for rc in f["rects_um"]:
        if abs(rc[3] - H0) < 1e-6: rc[3] = d["outline_um"][1]
r["die_outline"] = d["outline_um"]
# overlap + bounds check
rects = []
for q in P:
    o = pt[q["type"]]["outline_um"]; a, b = q["origin_um"]
    if q.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"): o = [o[1], o[0]]
    rects.append((q["name"], a, b, a+o[0], b+o[1]))
bad = []
rs = sorted(rects, key=lambda x: x[1])
for i, A in enumerate(rs):
    for B in rs[i+1:]:
        if B[1] >= A[3] - 1e-6: break
        if B[2] < A[4] - 1e-6 and B[4] > A[2] + 1e-6: bad.append((A[0], B[0]))
r["overlaps"] = bad[:20]; r["n_overlaps"] = len(bad)
r["out_of_die"] = [x[0] for x in rects if x[3] > d["outline_um"][0]+1e-6 or x[4] > d["outline_um"][1]+1e-6]
o = json.dumps(new, separators=(",", ":")).encode()
if raw.endswith(b"\n"): o += b"\n"
open(out, "wb").write(o); r["sha"] = hashlib.sha256(o).hexdigest()[:12]
rt = json.dumps(old, separators=(",", ":")).encode() + (b"\n" if raw.endswith(b"\n") else b"")
r["roundtrip_base_identical"] = (rt == raw)
json.dump(r, open(rep, "w"), indent=1, default=list)
print({k: (v if not isinstance(v, (list, dict)) or len(str(v)) < 300 else str(v)[:300]) for k, v in r.items()})
