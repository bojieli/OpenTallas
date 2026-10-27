#!/usr/bin/env python3
"""INFRA-FIRST-QC-R25 (COORD 06:34 ruling on R24b): mesh driver re-plan on the A0 R3b drop lattice, then the whole-die
linear-RC mesh transient (qc_clk_mesh2.solve_netlist, thev_r2 Thevenin drivers, RC_R6 8w strap RC) with the 16,896 A0
island drop loads.  Plan (12.8 d1: deterministic, computed from plan geometry before any build; section 12 unchanged):
  * straps = R24 re-phase: R23 straps outside the A0 field + every driver column + the R3b drop straps
    (M9 x0+U over each A0 column, M8 y0+V / y0+H-V over each A0 row, full die width as in R24);
  * DROP M9 SEGMENTED PER A0 ROW: each drop M9 spans only [band below its row, band above its row]; no full-height
    interior strap (R24: full die height, fed only through M8);
  * BAND DRIVERS: one mesh driver ON each drop M9 strap in each A0 row band (die-edge band, inter-row bands, the band
    towards the centre field), so each row segment is driven at both ends.  Site = the kept R23 M8 strap in the band
    (crossing) when it is not on a partition seam and not on a hard core (+ISL), else the band centre on the 8.64 lane;
  * W-EDGE DRIVER COLUMN at x = --wedge-x (default 1650.24 - 2 x 8.64 = 1632.96: island edge 12.96 um from the A0 W face, outside the 5.4 NK halo) (M9 full span, a driver at every M8 strap y), like R23 columns;
  * feed: every band driver is a leaf of the H-tree through a band leg from the nearest driver column (12.8c/d1:
    plan-computed sizing makes every leaf arrive at the common driver arrival at TT; the FF residual of that sizing
    = (D_FF(L) - D_FF(Lmax)) - rho (D_TT(L) - D_TT(Lmax)), rho = D_FF/D_TT of the pad, is applied to FF arrivals).
Mesh continuity: every geometric M9-segment x M8 crossing is ONE node (M8-M9 via) -- fail-closed check (count of
geometric crossings == crossing nodes, else exit 2).
usage: r25_drop_drivers.py R2 R3B QCDIR OUTDIR --thev T --stage S [--corner TT] [--samples N] [--mode replan|rephase]"""
import argparse, collections, json, math, random, sys, time
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument("r2"); ap.add_argument("r3b"); ap.add_argument("qc"); ap.add_argument("out")
ap.add_argument("--thev", required=True); ap.add_argument("--stage", required=True)
ap.add_argument("--corner", default="TT"); ap.add_argument("--samples", type=int, default=0)
ap.add_argument("--mode", default="replan", choices=["replan", "rephase", "nowedge", "nobands"])
ap.add_argument("--sigma", default='{"vt_mV": 10.0, "wire_rel": 0.05, "tree_ps_per_stage": 2.0}')
ap.add_argument("--drop-w", default=None, help="NDR of the drop M9 segments (default = mesh ndr)")
ap.add_argument("--wedge-x", type=float, default=1632.96,
                help="W-edge driver column x: 1650.24 - 2 x 8.64, so the 8.64 island keeps the 5.4-um NK halo and the A0 W pin face")
ap.add_argument("--feed-w", default="16w")
ap.add_argument("--size-rule", default="none", choices=["none", "adjcol"],
                help="plan-computed band-driver sizing (12.8 d1): adjcol = BUFx24 x2 on the band drivers of an A0 column "
                     "with fewer than 2 adjacent channel driver columns (W-edge column counts)"); ap.add_argument("--feed-m", type=int, default=2)
a = ap.parse_args()
sys.path.insert(0, a.qc)
import qc_clk_mesh2 as Q
import qc_clk_mesh as Q1
import qc_clk_mesh3 as M3
r3, ISL = Q.r3, 8.64
WX = a.wedge_x
CW, CH = 457.92, 1157.76
rec = json.load(open(a.r2)); R3 = json.load(open(a.r3b))
pkg = str(Path(a.r2).resolve().parents[2])
P, dtp, parts, cores, psha = Q1.load(rec["plan"].replace("/w/", pkg + "/"), rec["tree_plan"].replace("/w/", pkg + "/"))
L = R3["lattices"]["R23_d51_candidate"]; U, V = R3["type_lattice"]["m9_u"], R3["type_lattice"]["m8_v"]
inst = L["per_instance"]
cols0 = sorted({q["x0"] for q in inst}); rows0 = sorted({q["y0"] for q in inst})
W, H = rec["W"], rec["H"]
over_x = lambda x: any(c - 1e-6 <= x <= c + CW + 1e-6 for c in cols0)
over_y = lambda y: any(r - 1e-6 <= y <= r + CH + 1e-6 for r in rows0)
incore = lambda x, y, m=ISL: any(c[0] - m < x < c[2] + m and c[1] - m < y < c[3] + m for c in cores)
pseam = lambda x, y: any(p[0] <= x <= p[2] and (abs(y - p[1]) < ISL / 2 or abs(y - p[3]) < ISL / 2) for p in parts)
dcol = sorted({r3(x) for x in rec["driver_columns"]})
kx = sorted({r3(x) for x in rec["xs"] if not over_x(x) or r3(x) in set(dcol)})
ky = sorted({r3(y) for y in rec["ys"] if not over_y(y)})
dropx = sorted({r3(c + u) for c in cols0 for u in U})
dropy = sorted({r3(q["y0"] + (CH - v if q["mx"] else v)) for q in inst for v in V})
info = dict(drop_w=a.drop_w, mode=a.mode, a0_cols=len(cols0), a0_rows=len(rows0), kept_m9=len(kx), kept_m8=len(ky), drop_m9=len(dropx), drop_m8=len(dropy))
# ---- bands: per A0 row the band below / above (die edge, inter-row, towards the centre field)
rows_sorted = rows0
bands = []           # (y_lo, y_hi) of free bands adjacent to A0 rows
for i, y0 in enumerate(rows_sorted):
    lo = rows_sorted[i - 1] + CH if i and rows_sorted[i - 1] + CH < y0 + 1e-6 and y0 - (rows_sorted[i - 1] + CH) < 400 else max(0.0, y0 - 160.0)
    bands.append((r3(lo), r3(y0)))
    hi_next = rows_sorted[i + 1] if i + 1 < len(rows_sorted) else H
    top = y0 + CH
    if hi_next - top >= 400 or i + 1 == len(rows_sorted):
        bands.append((r3(top), r3(min(H, top + 160.0))))
bands = sorted(set(bands))
def band_y(lo, hi, x):
    """driver site y in a band: the kept M8 strap nearest the band centre (crossing), else the 8.64 lane at the centre;
    never on a partition seam or on a hard core (+ISL)."""
    yc = (lo + hi) / 2
    cand = sorted([y for y in ky if lo + ISL <= y <= hi - ISL], key=lambda y: abs(y - yc))
    cand += sorted([r3(k * ISL) for k in range(int(lo // ISL) + 1, int(hi // ISL) + 1) if lo + ISL / 2 <= k * ISL <= hi - ISL / 2],
                   key=lambda y: abs(y - yc))
    for y in cand:
        if not pseam(x, y) and not incore(x, y, ISL / 2):
            return r3(y)
    return None
Path(a.out).mkdir(parents=True, exist_ok=True)
# ---- straps: M8 (y, xl, xh) full span; M9 (x, yl, yh)
xmin = WX if a.mode in ("replan", "nobands") else min(kx + dropx)
xmax = max(kx + dropx)
yall = sorted(set(ky) | set(dropy))
H8 = [(y, xmin, xmax) for y in yall]
V9 = []
for x in kx:
    V9.append((x, yall[0], yall[-1]))
if a.mode in ("replan", "nobands"):
    V9.append((WX, yall[0], yall[-1]))
band_drv = []
row_of_band = collections.defaultdict(list)
if a.mode == "rephase":
    for x in dropx:
        V9.append((x, yall[0], yall[-1]))
else:
    for x in dropx:
        ybs = {}
        for b in bands:
            yb = band_y(b[0], b[1], x)
            if yb is None:
                raise SystemExit(f"no band driver site at x {x} band {b}")
            ybs[b] = yb
        for i, y0 in enumerate(rows_sorted):
            below = [b for b in bands if abs(b[1] - y0) < 1e-6][0]
            above = [b for b in bands if abs(b[0] - (y0 + CH)) < 1e-6 or (b[0] <= y0 + CH + 1e-6 and b[1] >= y0 + CH)]
            above = above[0]
            V9.append((x, ybs[below], ybs[above]))
        if a.mode == "replan":
            for b, yb in ybs.items():
                band_drv.append(dict(x=x, y=yb, band=b))
V9 = sorted(set(V9))
# ---- drivers
drivers = []
for n in rec["nodes"]:
    if n["driver"]:
        drivers.append(dict(tag=n["tag"], x=r3(n["site"][0]), y=r3(n["site"][1]), arr=n["arr"], parent=n["tag"], leg=0.0, kind="r23"))
by = {n["tag"]: n for n in rec["nodes"]}
if a.mode in ("replan", "nobands"):
    for y in yall:
        if incore(WX, y, ISL / 2):
            info["wedge_skipped_on_core"] = info.get("wedge_skipped_on_core", 0) + 1
            continue
        drivers.append(dict(tag=f"wedge_{y}", x=WX, y=y, arr=None, parent=None, leg=None, kind="wedge"))
adjcols = {}
for c in cols0:
    dc = set(dcol) | ({WX} if a.mode in ("replan", "nobands") else set())
    adjcols[c] = sum(1 for side in ((c - 200.0, c), (c + CW, c + CW + 200.0)) if any(side[0] <= x <= side[1] for x in dc))
for d in band_drv:
    c = max(q for q in cols0 if q <= d["x"])
    mult = 2 if a.size_rule == "adjcol" and adjcols[c] < 2 else 1
    drivers.append(dict(tag=f"band_{d['x']}_{d['y']}", x=d["x"], y=d["y"], arr=None, parent=None, leg=None, kind="band", mult=mult))
# feed legs: nearest R23 driver (column x, nearest row) -> |dx| + |dy| (band lane + column); balanced by plan sizing
r23 = [d for d in drivers if d["kind"] == "r23"]
bycol = collections.defaultdict(list)
for d in r23:
    bycol[d["x"]].append(d)
colx = sorted(bycol)
st = M3.Stage(a.stage); et = M3.EdgeType(st, a.feed_w, a.feed_m, 450.0)
for d in drivers:
    if d["kind"] == "r23":
        continue
    cx = min(colx, key=lambda c: abs(c - d["x"]))
    p = min(bycol[cx], key=lambda q: abs(q["y"] - d["y"]))
    d["parent"] = p["tag"]; d["leg"] = r3(abs(cx - d["x"]) + abs(p["y"] - d["y"]))
legs = [d["leg"] for d in drivers if d["kind"] != "r23"]
feed = {}
if legs:
    Lmax = max(legs)
    DT = lambda Lx, c: et.delay(max(Lx, 1.0), c)
    rho = DT(Lmax, "FF") / DT(Lmax, "TT")
    res = []
    for d in drivers:
        if d["kind"] == "r23":
            continue
        rff = (DT(d["leg"], "FF") - DT(Lmax, "FF")) - rho * (DT(d["leg"], "TT") - DT(Lmax, "TT"))
        a0 = by[d["parent"]]["arr"]
        d["arr"] = {"TT": a0["TT"], "FF": a0["FF"] + rff}
        d["ff_residual_ps"] = r3(rff); res.append(rff)
    feed = dict(n=len(legs), leg_um_max=r3(Lmax), leg_um_med=r3(sorted(legs)[len(legs) // 2]), stages_max=et.nseg(Lmax),
                D_TT_range_ps=[r3(DT(min(legs), "TT")), r3(DT(Lmax, "TT"))], D_FF_range_ps=[r3(DT(min(legs), "FF")), r3(DT(Lmax, "FF"))],
                rho=r3(rho), ff_residual_ps=[r3(min(res)), r3(max(res))],
                rule="plan-computed per-leaf sizing (12.8 d1): every new leaf arrives at its parent column driver arrival at TT; "
                     "FF residual = sizing tracking error, applied to FF arrivals")
# fail-closed site checks
bad = [d for d in drivers if d["kind"] != "r23" and incore(d["x"], d["y"], ISL / 2)]
if bad:
    raise SystemExit(f"{len(bad)} new drivers on a hard core, e.g. {bad[:3]}")
seam = [d for d in drivers if d["kind"] == "band" and pseam(d["x"], d["y"])]
info.update(size_rule=a.size_rule, adj_driver_cols_hist=dict(collections.Counter(adjcols.values())),
            band_x2=sum(1 for d in drivers if d.get("mult", 1) == 2), bands=len(bands), band_drivers=len(band_drv), wedge_drivers=sum(1 for d in drivers if d["kind"] == "wedge"),
            r23_drivers=len(r23), drivers=len(drivers), m9_segments=len(V9), m8=len(H8), new_on_core=0, band_on_seam=len(seam), feed=feed)
# ---- taps: partitions (rec taps) + A0 drops
taps = [dict(part=t["part"], x=r3(t["tap"][0]), y=r3(t["tap"][1]), stub=t["stub_um"]) for t in rec["taps"]]
for q in inst:
    for n, t in R3["islands"].items():
        u, v = t["drop_core_frame"]
        taps.append(dict(part=f"drop:{q['n']}:{n}", x=r3(q["x0"] + u), y=r3(q["y0"] + (CH - v if q["mx"] else v)), stub=0.0))
# ---- netlist
def build(seed, sg):
    rnd = random.Random(1000 * seed + 17)
    off = {}
    if seed and sg.get("tree_ps_per_stage"):
        for n in sorted(rec["nodes"], key=lambda n: len(n["tag"])):
            if n["parent"] is None:
                off[n["tag"]] = 0.0; continue
            nst = max(1, math.ceil(n["leg_um"] / 450.0 - 1e-9))
            off[n["tag"]] = off[n["parent"]] + rnd.gauss(0.0, sg["tree_ps_per_stage"] * math.sqrt(nst))
    hp = {i: {s[1], s[2]} for i, s in enumerate(H8)}
    vp = {i: {s[1], s[2]} for i, s in enumerate(V9)}
    yidx = collections.defaultdict(list)
    for i, s in enumerate(H8):
        yidx[s[0]].append(i)
    xidx = collections.defaultdict(list)
    for i, s in enumerate(V9):
        xidx[s[0]].append(i)
    xset = set()
    for j, (x, yl, yh) in enumerate(V9):
        for i, (y, xl, xh) in enumerate(H8):
            if yl - 1e-6 <= y <= yh + 1e-6 and xl - 1e-6 <= x <= xh + 1e-6:
                hp[i].add(x); vp[j].add(y); xset.add((x, y))
    ncross = len(xset)
    def attach(x, y):
        for i in yidx.get(y, ()):
            if H8[i][1] - 1e-6 <= x <= H8[i][2] + 1e-6:
                hp[i].add(x); return True
        for j in xidx.get(x, ()):
            if V9[j][1] - 1e-6 <= y <= V9[j][2] + 1e-6:
                vp[j].add(y); return True
        return False
    drv = []
    for d in drivers:
        if not attach(d["x"], d["y"]):
            raise SystemExit(f"driver {d['tag']} at {(d['x'], d['y'])} not on a strap")
        o = off.get(d["parent"], 0.0)
        if seed and d["kind"] != "r23" and sg.get("tree_ps_per_stage"):
            o += rnd.gauss(0.0, sg["tree_ps_per_stage"] * math.sqrt(max(1, math.ceil(d["leg"] / 450.0 - 1e-9))))
        for k in range(d.get("mult", 1)):     # a x2 driver = two parallel BUFx24 units at the same node (own mismatch each)
            drv.append(dict(tag=d["tag"] + (f"#{k}" if k else ""), node=("P", d["x"], d["y"]), arr=d["arr"][a.corner] + o,
                            dvn=[rnd.gauss(0, sg.get("vt_mV", 0) / 1e3) if seed else 0.0], dvp=[rnd.gauss(0, sg.get("vt_mV", 0) / 1e3) if seed else 0.0]))
    tps, unatt = [], 0
    for t in taps:
        if not attach(t["x"], t["y"]):
            unatt += 1; continue
        tps.append(dict(part=t["part"], node=("P", t["x"], t["y"]), stub=t["stub"], inside=True,
                        dvn=rnd.gauss(0, sg.get("vt_mV", 0) / 1e3) if seed else 0.0, dvp=rnd.gauss(0, sg.get("vt_mV", 0) / 1e3) if seed else 0.0))
    nid = {}
    def node(k):
        if k not in nid:
            nid[k] = "n%d" % len(nid)
        return nid[k]
    R, C = [], collections.defaultdict(float)
    wr = sg.get("wire_rel", 0.0) if seed else 0.0
    rr = Q.RC_R6[rec["ndr"]]
    rd = Q.RC_R6[a.drop_w or rec["ndr"]]
    dset = set(dropx)
    def wire(ka, kb, Lw, layer, drop=False):
        r, c = (rd if drop else rr)[layer]
        n = max(1, int(math.ceil(Lw / 54.0)))
        prev = node(ka)
        for q in range(1, n + 1):
            cur = node(kb) if q == n else node((ka, kb, q))
            f = rnd.gauss(1.0, wr) if wr else 1.0
            R.append((prev, cur, r * Lw / n * f)); C[prev] += c * Lw / n / 2 * f; C[cur] += c * Lw / n / 2 * f
            prev = cur
    for i, pts in hp.items():
        y = H8[i][0]; p = sorted(pts)
        for u_, w_ in zip(p, p[1:]):
            if w_ - u_ > 1e-9:
                wire(("P", u_, y), ("P", w_, y), w_ - u_, "M8")
    for j, pts in vp.items():
        x = V9[j][0]; p = sorted(pts)
        for u_, w_ in zip(p, p[1:]):
            if w_ - u_ > 1e-9:
                wire(("P", x, u_), ("P", x, w_), w_ - u_, "M9", drop=x in dset)
    # fail-closed via check: every geometric crossing is one shared node
    xn = {}
    for j, (x, yl, yh) in enumerate(V9):
        for i, (y, xl, xh) in enumerate(H8):
            if yl - 1e-6 <= y <= yh + 1e-6 and xl - 1e-6 <= x <= xh + 1e-6:
                xn[(x, y)] = nid.get(("P", x, y))
    missing = sum(1 for v in xn.values() if v is None)
    if missing or len(xn) != ncross:
        raise SystemExit(f"FAIL-CLOSED via check: {missing} crossings without a node, {len(xn)} vs {ncross}")
    for d in drv:
        d["node"] = node(d["node"])
    for t in tps:
        t["node"] = node(t["node"]); C[t["node"]] += Q.BUF_CIN_FF
    return dict(R=R, C=C, drv=drv, taps=tps, xnodes=xn, nodes=len(nid), crossings=ncross, vias=ncross, unattached=unatt)
sig = json.loads(a.sigma); thev = json.load(open(a.thev))
out = dict(info=info, corner=a.corner, sigma=sig, samples=[])
print(json.dumps(info), flush=True)
json.dump(dict(info=info, H8=H8, V9=V9, drivers=[{k: v for k, v in d.items()} for d in drivers if d["kind"] != "r23"], bands=bands),
          open(Path(a.out) / f"plan_{a.mode}.json", "w"))
for s in range(a.samples + 1):
    t1 = time.time()
    N = build(s, sig)
    ctot = sum(N["C"].values())
    resd, t0 = Q.solve_netlist(N, a.corner, thev)
    xc = [v for k, v in resd.items() if k[0] == "x"]
    tp = {k[1]: v for k, v in resd.items() if k[0] == "t"}
    pt = [v for k, v in tp.items() if not k.startswith("drop:")]
    dp = [v for k, v in tp.items() if k.startswith("drop:")]
    xa0 = [v for k, v in resd.items() if k[0] == "x" and over_x(k[1][0]) and over_y(k[1][1])]
    row = dict(sample=s, nodes=N["nodes"], crossings=N["crossings"], vias=N["vias"], drivers=len(N["drv"]), taps_attached=len(N["taps"]),
               taps_unattached=N["unattached"], c_total_pf=r3(ctot / 1000),
               crossing_spread_ps=r3(max(xc) - min(xc)), a0_field_crossing_spread_ps=r3(max(xa0) - min(xa0)) if xa0 else None,
               part_tap_skew_ps=r3(max(pt) - min(pt)) if pt else None, drop_n=len(dp), drop_skew_ps=r3(max(dp) - min(dp)) if dp else None,
               all_tap_skew_ps=r3(max(tp.values()) - min(tp.values())), t_first=r3(min(tp.values())), t_last=r3(max(tp.values())),
               secs=round(time.time() - t1, 1))
    bc = collections.defaultdict(list)
    for k, v in tp.items():
        if k.startswith("drop:"):
            bc[k.split(":")[1]].append(v)
    if bc:
        sp = sorted((max(v) - min(v), k) for k, v in bc.items())
        row["in_core_drop_spread_ps"] = dict(n=len(sp), median=r3(sp[len(sp) // 2][0]), p90=r3(sp[int(len(sp) * 0.9)][0]), max=r3(sp[-1][0]), worst=sp[-1][1])
    late = sorted(tp.items(), key=lambda kv: -kv[1])[:5]
    row["latest"] = [(k, r3(v)) for k, v in late]
    if s == 0:
        row["tap_arr_ps"] = {k: r3(v) for k, v in tp.items()}
        row["crossing_arr_ps"] = {f"{k[1][0]},{k[1][1]}": r3(v) for k, v in resd.items() if k[0] == "x"}
    out["samples"].append(row)
    print(json.dumps({k: v for k, v in row.items() if k not in ("tap_arr_ps", "crossing_arr_ps")}), flush=True)
    json.dump(out, open(Path(a.out) / f"mc_{a.mode}_{a.corner}.json", "w"))
