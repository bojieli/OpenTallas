#!/usr/bin/env python3
"""FABLE-FIX-QC-SLE-R3 plan delta for the su_c class (sle_su_c, slw_su_c__cl19bb38ef, slw_su_c__cl92142dac): station sites off the hard cores.
  su_delta.py PLAN_IN TYPE PINS_PKL BOUND_SV PLAN_OUT ROWS_OUT REPORT PLAN_OF_RECORD_DIR
Same class as sle_ctl (FABLE-FIX-QC-SLE-R2): the per-bit knee model of the out-bus station chains runs straight from a nominal leaf to
the face and lands stations inside (and routes over) the 9 hard cores, which block M1-M5.  No core moves here: the cores already leave
a 121-um street (y 276-397), the W / E margins and the top half free.  Every bit of x_su_l0_o, x_su_l0_p1_o, x_su_l1_p1_o, x_ctl_o,
x_sc_o gets its own core-free polyline from its TRUE source (bound RTL u_bout_<bus> .d concat: su8 / red core pin, or the soft
vm8out register next to its memory core) to its face pin, stations at equal arclength (plan relay_sites u_ist_<bus>_<k>.q[b] / .eq,
the kit's rs_place_all form).  In-bus lane pads: regs_um moved onto a core-free centre line (packed model).
Station counts are kept (0 cycles) unless MAXHOP (um, default off) is set: then a chain whose worst hop exceeds it gets stations
added (+1 cycle each on the lanes launched from that bus on partitions of this type)."""
import json, pickle, sys, re, os, math
pin_, TN, pkl, bsv, pout, rout, rep_, PLAN_DIR = sys.argv[1:9]
TAG = os.environ.get("SLE_TAG", "FABLE-FIX-QC-SLE-R3 11-21"); MAXHOP = float(os.environ.get("MAXHOP", "0"))
P = json.load(open(pin_)); t = P["partition_types"][TN]
_t0, PINS = pickle.load(open(pkl, "rb"))
hc = {c["inst"]: c for c in t["hard_cores"]}
BOX = {k: (c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1]) for k, c in hc.items()}
def cpins(inst):
    c = hc[inst]; pj = json.load(open(PLAN_DIR + c["pins_file"])); pl = pj if isinstance(pj, list) else pj["pins"]; o = {}
    for p in pl:
        if "bus" in p: nm, b = p["bus"], int(p.get("bit") or 0)
        else:
            m = re.match(r"(.*?)(?:\[(\d+)\])?$", p["name"]); nm, b = m.group(1), int(m.group(2) or 0)
        o[(nm, b)] = (c["origin_um"][0] + float(p["x"]), c["origin_um"][1] + float(p["y"]))
    return o
SU = cpins("u_suvm_u_su8"); RD = cpins("u_red_u_core")
B = lambda k: BOX["u_suvm_u_vm8q_u_" + k]
va, vb, vc, cl, pg, ch, bt = B("va"), B("vb"), B("vc"), B("cl"), B("pg"), B("ch"), B("bt"); su8 = BOX["u_suvm_u_su8"]; red = BOX["u_red_u_core"]
OX, OY = t["outline_um"]
assert abs(su8[2] - 509.76) < 0.1 and abs(ch[0] - 544.32) < 0.1 and abs(pg[2] - 302.4) < 0.1 and abs(red[1] - 596.16) < 0.1 and abs(bt[3] - 552.96) < 0.1, "su_c floorplan changed: re-derive the corridors"
md = lambda a, c: abs(a[0] - c[0]) + abs(a[1] - c[1])
def plen(pts): return sum(md(a, c) for a, c in zip(pts, pts[1:]))
def at(pts, s):
    for a, c in zip(pts, pts[1:]):
        d = md(a, c)
        if s <= d + 1e-9:
            f = s / d if d else 0.0
            return (a[0] + f * (c[0] - a[0]), a[1] + f * (c[1] - a[1]))
        s -= d
    return pts[-1]
def seg_hits(a, c, box, tol=0.5):
    x0, x1, y0, y1 = min(a[0], c[0]), max(a[0], c[0]), min(a[1], c[1]), max(a[1], c[1])
    return x0 < box[2] - tol and x1 > box[0] + tol and y0 < box[3] - tol and y1 > box[1] + tol
def inbox(p, box, h=0.0): return box[0] - h < p[0] < box[2] + h and box[1] - h < p[1] < box[3] + h
ist = {e["conn"][4:]: e for e in t["internal_stations"] if e["conn"].startswith("bus:")}
N0 = {k: len(e["regs_um"]) for k, e in ist.items()}
rs = t.setdefault("relay_sites", {}); REP = {"type": TN, "rows": {}, "note": TAG, "boxes": BOX}
# ---- true source of every bit: u_bout_<bus> .d({...}) of the bound RTL (MSB first)
SRC = open(bsv).read()
def sources(bus):
    m = re.search(r"\bu_bout_%s\s*\(.*?\.d\(\{(.*?)\}\)" % re.escape(bus), SRC, re.S); assert m, bus
    segs = []
    for tok in m.group(1).split(","):
        mm = re.match(r"\s*(\w+)\s*(?:\[(\d+)(?::(\d+))?\])?\s*$", tok); assert mm, tok
        net = mm.group(1); hi = int(mm.group(2)) if mm.group(2) else None; lo = int(mm.group(3)) if mm.group(3) else hi
        segs.append((net, hi, lo))
    out = []
    for net, hi, lo in reversed(segs):
        assert hi is not None, (bus, net)
        for i in range(lo, hi + 1): out.append((net, i))
    return out
def where(net, i):
    """-> (group, source point or None)"""
    m = re.match(r"w_u_suvm_u_su8_(\w+)$", net)
    if m: return "su8_" + m.group(1), SU.get((m.group(1), i))
    m = re.match(r"w_u_red_(red_\w+)$", net)
    if m: return "red", RD.get((m.group(1), i))
    m = re.match(r"w_u_suvm_u_vm8q_u_(o\w+)_q$", net)
    if m: return m.group(1), None
    return "soft", None
# ---- corridors
HY0, HY1 = va[3], su8[1]                       # the street between the two core rows (276.48 .. 397.44)
YL = (HY0 + 6.0, HY0 + 32.0)                   # lower band: x_su_l0_o (the x_su_l1_o banks keep y 315-346)
YU0 = (HY1 - 46.0, HY1 - 27.0)                 # upper band a: x_su_l0_p1_o
YU1 = (HY1 - 23.0, HY1 - 5.0)                  # upper band b: x_su_l1_p1_o
GE = (su8[2] + 4.0, ch[0] - 4.0)               # su8 | ch gap (x)
GW = (pg[2] + 4.0, su8[0] - 4.0)               # pg | su8 gap (x)
lerp = lambda r, f: r[0] + (r[1] - r[0]) * f
ANCH = {"oa": (va[0] - 16.0, va[3] - 30.0), "ob": (vb[0] - 10.0, vb[3] - 30.0), "oc": (vc[0] - 12.0, vc[3] - 30.0), "ocl": (cl[0] - 8.0, cl[3] - 30.0),
        "och": (ch[0] - 6.0, ch[3] - 22.0)}   # the vm8out output registers sit at the q pins (W face) of their memory core
def p_l0(b, f, g, grp, src, px, py):           # E face, pins beside / under the street
    yb = lerp(YL, f); xe = cl[2] + 6.0 + (OX - cl[2] - 14.0) * f
    tail = [(xe, yb), (xe, py), (px, py)]
    if grp == "su8_gb": xg = lerp((GE[0], GE[0] + 10.0), g); return [src, (xg, src[1]), (xg, yb)] + tail
    if grp == "su8_pd1": xg = lerp((GE[0] + 12.0, GE[1]), g); ya = su8[3] + 5.0 + 9.0 * g; return [src, (src[0], ya), (xg, ya), (xg, yb)] + tail
    if grp.startswith("su8_") and src: return [src, (src[0], yb)] + tail
    return [(su8[2] - 40.0, yb)] + tail
def p_l0p1(b, f, g, grp, src, px, py):         # E face, pins beside bt
    yb = lerp(YU0, f); xe = OX - 10.0 - (OX - bt[2] - 18.0) * f
    tail = [(xe, yb), (xe, py), (px, py)]
    if grp == "su8_pd1": xg = lerp((GE[0] + 12.0, GE[1]), g); ya = su8[3] + 16.0 + 6.0 * g; return [src, (src[0], ya), (xg, ya), (xg, yb)] + tail
    if grp == "och":                           # over ch, down the ch | bt gap, east between bt and red
        a = ANCH["och"]; ya = ch[3] + 8.0 + 14.0 * g; xd = ch[2] + 8.0 + 28.0 * g; yc = bt[3] + 6.0 + 30.0 * (1 - g); xr = red[2] + 6.0 + (OX - red[2] - 14.0) * g
        return [a, (a[0], ya), (xd, ya), (xd, yc), (xr, yc), (xr, py), (px, py)]
    a = ANCH.get(grp)
    if a: return [a, (a[0], yb)] + tail
    return [(su8[2] - 40.0, yb)] + tail
def p_l1p1(b, f, g, grp, src, px, py):         # W face, pins beside pg
    yb = lerp(YU1, f); xw = 8.0 + (pg[0] - 16.0) * f
    tail = [(xw, yb), (xw, py), (px, py)]
    if grp == "su8_pd1": xg = lerp((GW[0], GW[0] + 12.0), g); ya = su8[3] + 26.0 + 8.0 * g; return [src, (src[0], ya), (xg, ya), (xg, yb)] + tail
    if grp == "och": a = ANCH["och"]; xg = lerp((GW[0] + 14.0, GW[1]), g); ya = su8[3] + 40.0 + 20.0 * g; return [a, (a[0], ya), (xg, ya), (xg, yb)] + tail
    if grp == "oa": a = ANCH["oa"]; return [a, (xw, a[1]), (xw, py), (px, py)]
    a = ANCH.get(grp)
    if a: return [a, (a[0], yb)] + tail
    return [(su8[0] + 40.0, yb)] + tail
def p_ctl(b, f, g, grp, src, px, py):          # N face (x 95-111)
    if grp == "red":                           # under red, up the ch | red gap, west above pg
        src = src or (red[0] + 135.0, red[1])
        yc = bt[3] + 8.0 + 26.0 * g; xu = red[0] - 28.0 + 8.0 * g; yt = red[3] + 30.0 + 20.0 * f
        return [src, (src[0], yc), (xu, yc), (xu, yt), (px, yt), (px, py)]
    xg = lerp((GW[0] + 6.0, GW[1] - 4.0), g); yt = pg[3] + 12.0 + 16.0 * f; yb = HY1 - 3.0
    s = src if src else (su8[0] + 45.0, su8[1])
    if abs(s[1] - su8[1]) < 1.0: return [s, (s[0], yb), (xg, yb), (xg, yt), (px, yt), (px, py)]            # su8 S pins
    if abs(s[0] - su8[0]) < 1.0: return [s, (xg, s[1]), (xg, yt), (px, yt), (px, py)]                      # su8 W pins
    ya = su8[3] + 4.0; return [s, (s[0], ya), (xg, ya), (xg, yt), (px, yt), (px, py)]                      # su8 N pins
def p_sc(b, f, g, grp, src, px, py):           # N face (x 994-1004): under red, up its W side, east above it
    s = src if src else (red[0] + 135.0, red[1])
    yc = bt[3] + 8.0 + 26.0 * g; xu = red[0] - 16.0 + 8.0 * g; yt = red[3] + 12.0 + 12.0 * f
    return [s, (s[0], yc), (xu, yc), (xu, yt), (px, yt), (px, py)]
XM = {}
def chain(bus, pathf, note):
    e = ist[bus]; pp = PINS[bus]; W = max(pp); n0 = len(e["regs_um"]); sr = sources(bus)
    assert len(sr) == W, (bus, len(sr), W)
    order = sorted(range(W + 1), key=lambda b: (pp[b][1], pp[b][0]) if pp[0][2] in "EW" else (pp[b][0], pp[b][1])); rank = {b: i for i, b in enumerate(order)}
    grp = {}; gi = {}
    for b in range(W):
        gname, s = where(*sr[b]); grp[b] = (gname, s); gi.setdefault(gname, []).append(b)
    grp[W] = (grp[W - 1][0] if not grp[W - 1][1] else "soft", None); gi.setdefault(grp[W][0], []).append(W)
    gpos = {b: (i + 0.5) / len(v) for v in gi.values() for i, b in enumerate(v)}
    paths = {}; Lmax = 0.0; cross = 0
    for b in range(W + 1):
        px, py, _f = pp[b]; gname, s = grp[b]
        pts = pathf(b, (rank[b] + 0.5) / (W + 1), gpos[b], gname, s, px, py)
        pts = [p for i, p in enumerate(pts) if i == 0 or md(p, pts[i - 1]) > 1e-6]
        for a, c in zip(pts, pts[1:]):
            assert abs(a[0] - c[0]) < 1e-6 or abs(a[1] - c[1]) < 1e-6, (bus, b, a, c)
            hb = [nm for nm, bx in BOX.items() if seg_hits(a, c, bx)]
            if hb: cross += 1; XM.setdefault(bus, {}).setdefault(hb[0], 0); XM[bus][hb[0]] += 1; break
        paths[b] = pts; Lmax = max(Lmax, plen(pts))
    n = n0
    if MAXHOP and Lmax / (n0 + 1) > MAXHOP: n = int(math.ceil(Lmax / MAXHOP)) - 1
    for k in list(rs):
        if k.startswith(f"u_ist_{bus}_"): del rs[k]
    sums = [[0.0, 0.0] for _ in range(n)]; incore = 0; hopmax = 0.0; gh = {}
    for b in range(W + 1):
        pts = paths[b]; L = plen(pts); prev = pts[0]
        gh[grp[b][0]] = max(gh.get(grp[b][0], 0.0), L / (n + 1))
        for k in range(n):
            s = at(pts, L * (k + 1) / (n + 1))
            if any(inbox(s, bx, 2.0) for bx in BOX.values()): incore += 1
            hopmax = max(hopmax, md(prev, s)); prev = s
            rs[f"u_ist_{bus}_{k}." + (f"q[{b}]" if b < W else "eq")] = [round(s[0], 3), round(s[1], 3)]; sums[k][0] += s[0]; sums[k][1] += s[1]
        hopmax = max(hopmax, md(prev, pts[-1]))
    e["regs_um"] = [[round(x / (W + 1), 3), round(y / (W + 1), 3)] for x, y in sums]
    for k in range(n):                                  # nominal bank point: the centroid, or the median bit's site when the centroid is in a core
        if any(inbox(e["regs_um"][k], bx, 1.0) for bx in BOX.values()): e["regs_um"][k] = list(rs[f"u_ist_{bus}_{k}.q[{order[W // 2]}]"])
    for kk in ("bit_sites_um",):
        e.pop(kk, None)
    lf = [round(sum(paths[b][0][0] for b in paths) / (W + 1), 3), round(sum(paths[b][0][1] for b in paths) / (W + 1), 3)]
    e["leaf_um"] = lf; e["from_um"] = lf
    e["note"] = (e.get("note", "") + f" | {TAG}: {note}; per-bit FIRM sites in relay_sites (u_ist_{bus}_<k>.q[b]) on core-free routes from the true "
                 f"sources, equal arclength per bit, worst hop {hopmax:.1f} um" + (f", {n0} -> {n} stations (+{n - n0} cycles)" if n != n0 else ", 0 cycles")).strip(" |")
    REP["rows"][bus] = dict(stations=n, stations_before=n0, bits=W + 1, worst_hop_um=round(hopmax, 1), longest_route_um=round(Lmax, 1),
                            worst_hop_by_source_um={k: round(v, 1) for k, v in gh.items()}, bits_by_source={k: len(v) for k, v in gi.items()},
                            routes_crossing_hard_cores=cross, sites_in_core=incore)
    return n - n0
ADD = {}
ADD["x_su_l0_o"] = chain("x_su_l0_o", p_l0, "su8 E / N pins down the su8|ch gap, east in the street lower band, E margin to the pins")
ADD["x_su_l0_p1_o"] = chain("x_su_l0_p1_o", p_l0p1, "vm8out registers east in the street upper band; och over ch and between bt and red; up the E margin")
ADD["x_su_l1_p1_o"] = chain("x_su_l1_p1_o", p_l1p1, "vm8out registers west in the street upper band; och / pd1 down the pg|su8 gap; up the W margin")
ADD["x_ctl_o"] = chain("x_ctl_o", p_ctl, "su8 bits up the pg|su8 gap and over pg; red bits under red, up its W side, west above pg")
ADD["x_sc_o"] = chain("x_sc_o", p_sc, "under red, up its W side, east above it")
# ---- in-bus lane pads: regs_um (packed model) on a core-free centre line; counts kept
def setregs(bus, pts, note):
    e = ist.get(bus)
    if not e: return
    n = len(e["regs_um"]); L = plen(pts)
    assert not any(seg_hits(a, c, bx) for a, c in zip(pts, pts[1:]) for bx in BOX.values()), bus
    was = sum(1 for r in e["regs_um"] if any(inbox(r, bx, 0.5) for bx in BOX.values()))
    e["regs_um"] = [[round(v, 3) for v in at(pts, L * (k + 1) / (n + 1))] for k in range(n)]
    e["note"] = (e.get("note", "") + f" | {TAG}: {note} ({was} of {n} pad sites were inside a hard core), hop {L / (n + 1):.1f} um, 0 cycles").strip(" |")
    REP["rows"][bus] = dict(stations=n, regs_in_core_before=was, hop_um=round(L / (n + 1), 1), regs_um=e["regs_um"])
def cy(bus): return sum(p[1] for p in PINS[bus].values()) / len(PINS[bus])
def cx(bus): return sum(p[0] for p in PINS[bus].values()) / len(PINS[bus])
for bus in ("x_ctl_p1_i", "x_ctl_p2_i"):
    e = ist.get(bus)
    if not e: continue
    lf = tuple(e["leaf_um"]); x0 = cx(bus); xd = ch[2] + 14.0 + (10.0 if bus.endswith("p2_i") else 0.0); yt = red[3] + 25.0 + (15.0 if bus.endswith("p2_i") else 0.0)
    yb = min(max(lf[1], HY0 + 8.0), HY1 - 8.0)
    end = lf if not any(inbox(lf, bx, 0.5) for bx in BOX.values()) else (xd, yb)
    pts = [(x0, OY), (x0, yt), (xd, yt), (xd, yb), (end[0], yb), end] if x0 > red[0] - 4.0 else [(x0, OY), (x0, ch[3] + 20.0), (xd, ch[3] + 20.0), (xd, yb), (end[0], yb), end]
    setregs(bus, pts, "pad stages down the ch|bt gap into the street (W of red)")
for bus in ("x_su_l0_i", "x_su_l0_p1_i"):
    e = ist.get(bus)
    if not e: continue
    lf = tuple(e["leaf_um"]); y0 = cy(bus); xe = OX - 22.0
    if lf[1] < va[1]:                                   # sinks under the bottom core row (slw cl19 form): along the S strip
        ys = va[1] - 28.0
        pts = [(OX, y0), (xe, y0), (xe, ys), (lf[0], ys)] if y0 > va[1] - 4.0 else [(OX, y0), (lf[0], y0)]
    else:                                               # sinks at su8: E margin, street, su8|ch gap
        yb = (YL[1] + 3.0) if bus.endswith("p1_i") else (YU0[0] - 3.0)      # between the station bands and the x_su_l1_o banks (y 315-346)
        xg = (GE[0] + GE[1]) / 2.0
        end = (xg, min(max(lf[1], yb), su8[3] - 10.0))
        pts = [(OX, y0), (xe, y0), (xe, yb), (xg, yb), end]
    setregs(bus, pts, "pad stages along the E margin and the street (not through cl / vc / bt / ch)")
# ---- residual census + lanes
left = [k for k, v in rs.items() if any(inbox(v, bx, 0.5) for bx in BOX.values())]
pre = {}
for k in left: a = re.sub(r"[\[./].*", "", k); pre[a] = pre.get(a, 0) + 1
REP["relay_sites_in_core"] = len(left); REP["relay_sites_in_core_by_block"] = pre
REP["regs_in_core"] = [e["conn"] for e in t["internal_stations"] for r in e["regs_um"] if any(inbox(r, bx, 0.5) for bx in BOX.values())]
REP["ft_regs_in_core"] = [s["name"] for s in t.get("ft_slots", []) for r in (s.get("regs_um") or []) if any(inbox(r, bx, 0.5) for bx in BOX.values())]
REP["routes_over_cores"] = XM; REP["added_cycles"] = {k: v for k, v in ADD.items() if v}
ptype = {x["name"]: x["type"] for x in P["partitions"]}
ports = P["ports"] if isinstance(P["ports"], dict) else {x["id"]: x for x in P["ports"]}
lanes = []
for l in P["lanes"]:
    a = ports[l["ports"][0]].get("src"); d = ADD.get((a or {}).get("bus"), 0)
    if a and d and ptype.get(a.get("part")) == TN:
        l["fixed_cycles"] = int(l.get("fixed_cycles", 0)) + d; r = P["latency"]["lanes"][l["id"]]
        for k in ("fixed", "cycles", "natural"): r[k] = int(r[k]) + d
        lanes.append([l["id"], d, r["cycles"]])
REP["lanes_raised"] = lanes; REP["relay_sites_total"] = len(rs)
t["note"] = (t.get("note", "") + f" | {TAG}: out-bus station sites per bit on core-free routes from the true sources (lanes/handoff/FABLE-FIX-QC-SLE-R3.md)").strip(" |")
json.dump(P, open(pout, "w"), separators=(",", ":"))
json.dump({"partition_types": {TN: t}, "lanes_raised": lanes, "note": TAG + ": apply = replace the type" + (" + fixed_cycles/latency.lanes +d on lanes_raised" if lanes else " (no latency change)")}, open(rout, "w"), separators=(",", ":"))
json.dump(REP, open(rep_, "w"), indent=1)
print(json.dumps({k: v for k, v in REP.items() if k != "boxes"}, indent=1)[:7000])
