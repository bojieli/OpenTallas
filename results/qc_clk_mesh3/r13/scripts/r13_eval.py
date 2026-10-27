"""INFRA-FIRST-QC-R13 option evaluation (plan model, ngspice stage table; UNCHECKED unless stated).
(a) die-level cells only outside partition outlines; (b) strict in-partition periodic top tree;
(a+b) hybrid: ONE die-level centre channel x-tree + per-period identical (x-periodic, y-mirror) vertical + local trees."""
import sys, json, math
from collections import defaultdict, Counter
sys.path.insert(0, sys.argv[1])
import qc_clk_mesh3 as Q3
import numpy as np
r2, stage, out = sys.argv[2], sys.argv[3], sys.argv[4]
class A: pass
a = A(); a.r2 = r2
rec, P, dtp, parts, cores, cols, gaps, rows, m, dy = Q3.lattice(a)
st = Q3.Stage(stage)
top = Q3.EdgeType(st, "16w", 2, 450.0)
W, H = rec["W"], rec["H"]; YC = H / 2
R = {}
PER = 2471.04
rects = {n: P.rect(n) for n in P.parts}
# ---------------- (a) die-level only
xs = np.arange(5, W, 10.0); ys = np.arange(5, H, 10.0)
cov = np.zeros((len(xs), len(ys)), bool)
for n, (x0, y0, x1, y1) in rects.items():
    cov[np.ix_((xs >= x0) & (xs < x1), (ys >= y0) & (ys < y1))] = True
ix, iy = np.nonzero(~cov)
fx = float(xs[ix].max()) if len(ix) else None
far = max(cols) - fx
R["a"] = dict(uncovered_frac=round(float((~cov).mean()), 4), uncovered_x_max_um=fx, uncovered_y=[float(ys[iy].min()), float(ys[iy].max())],
              farthest_col_tap_x=max(cols), unrepeated_gap_um=round(far, 1), reach_um=450, verdict="FAIL (reach)",
              stages_needed_in_partitions=math.ceil(far / 450))
# ---------------- (b) strict periodic in-partition: per-period identical content -> row distribution is a chain
d_st = {c: st.seg("16w", 2, c, PER / 6) for c in ("TT", "FF")}
nper = 12
half = nper / 2
R["b"] = dict(stage_um=round(PER / 6, 2), stages_per_period=6, stage_ps={c: round(v, 2) for c, v in d_st.items()},
              row_spread_ps={c: round(6 * half * d_st[c], 1) for c in d_st},
              neighbour_period_skew_ps={c: round(6 * d_st[c], 1) for c in d_st},
              note="any per-type-identical in-partition content is x-periodic (12 instances/row at 2471.04 pitch); "
                   "a periodic chain fed at the row centre arrives linearly in x; per-tap sizing moves a tap by ~10-30 ps",
              verdict="FAIL (nominal spread vs 20 ps target; mesh drivers 6 stages apart short each other)")
# ---------------- (a+b) hybrid
Q3.ISLANDS[0] = None; Q3.BLOCK[0] = None
trunk = [c for c in cols if any(abs(c - (2177.28 + PER * k)) < 0.5 for k in range(12))]
assert len(trunk) == 12, trunk
OFF = [0.0, 622.08, 1235.52, 1866.24]
# local rows: bottom gap rows (seam rows nudged 8.64 into the partition farther from the centre), top = exact mirror
seams = sorted({round(r[1], 2) for r in rects.values()} | {round(r[3], 2) for r in rects.values()})
def onseam(y): return any(abs(y - s) < 1e-3 for s in seams)
gb = [g for g in gaps if g < YC - 1]
assert len(gb) == 9 and abs(gaps[9] - YC) < 1e-3
lb = [g + 8.64 if onseam(g) else g for g in gb]   # seam rows -> partition nearer the centre (cbx rows 2/4 then host the same 2 rows)
lb.append(YC - 8.64)                     # centre group: bottom half-tree tap (centre fine-driver row shared by the two halves)
lt = [H - y for y in lb]
loc_rows = sorted(lb + lt)
K = 5
x0t = trunk[K]
nodes = []
def local(y, tag):
    leaves = [(x0t + o, y) for o in OFF]
    r = Q3.dtree(leaves, "x", top, tag, nodes)
    if abs(r["xy"][0] - x0t) > 1e-6:
        r = Q3.lift(r, (x0t, y), top, tag + "L", nodes)
    return r
def ysub(ylist, tag):
    rs = [local(y, f"{tag}r{i:02d}_") for i, y in enumerate(ylist)]
    def yt(items, t):
        if len(items) == 1:
            return items[0]
        h = len(items) // 2
        return Q3.merge(yt(items[:h], t + "0"), yt(items[h:], t + "1"), "y", top, t, nodes)
    return yt(rs, tag)
B = ysub(sorted(lb), "B")
# top half = exact mirror of B (geometry), timing identical by construction
nB = list(nodes)
def mir(n):
    q = dict(n); q["tag"] = "M" + n["tag"]; q["xy"] = (n["xy"][0], H - n["xy"][1]); q["kids"] = ["M" + k for k in n["kids"]]
    if n.get("parent"): q["parent"] = "M" + n["parent"]
    return q
nodes += [mir(n) for n in nB]
T = dict(B); Tm = [n for n in nodes if n["tag"] == "M" + B["tag"]][0]
# root of the mirrored pair: exactly on the centre line (symmetric legs, equal stages by construction)
Lc = abs(YC - B["xy"][1]); nc = top.nseg(Lc)
for ch_ in (B, Tm):
    ch_["parent"], ch_["leg"], ch_["nseg"], ch_["et"] = "Y", Lc, nc, top
yroot = dict(tag="Y", xy=(x0t, YC), kids=[B["tag"], Tm["tag"]], T={c: B["T"][c] + top.delay(Lc, c, nc) for c in ("TT", "FF")}, S=B["S"] + nc)
nodes.append(yroot)
per_col = list(nodes)
# stage / timing per leaf (one column)
by = {n["tag"]: n for n in nodes}
def arr(n):
    return n["T"]
leaves = [n for n in nodes if not n["kids"]]
# path delay from yroot to every leaf = yroot.T - (slack) : nodes hold T = max over kids; recompute exact per leaf
def path_T(leaf, c):
    t, tot = leaf, 0.0
    while t.get("parent"):
        p = by[t["parent"]]
        tot += top.delay(t["leg"], c, t["nseg"]); t = p
    return tot, t["tag"]
lt_ = {c: [path_T(l, c)[0] for l in leaves] for c in ("TT", "FF")}
stages = Counter()
for l in leaves:
    s, t = 0, l
    while t.get("parent"):
        s += t["nseg"]; t = by[t["parent"]]
    stages[s] += 1
# channel x-tree over the 12 column roots (die-level cells in the channel)
cn = []
croots = [dict(tag=f"H{k:02d}", xy=(x, YC), kids=[], T=dict(yroot["T"]), S=yroot["S"]) for k, x in enumerate(trunk)]
cn += croots
hr = Q3.dtree([r["xy"] for r in croots], "x", top, "H", cn, leafmk=lambda xy, tag: [r for r in croots if abs(r["xy"][0] - xy[0]) < 1e-6][0])
cby = {n["tag"]: n for n in cn}
def cpath(n, c):
    t, tot, s = n, 0.0, 0
    while t.get("parent"):
        tot += top.delay(t["leg"], c, t["nseg"]); s += t["nseg"]; t = cby[t["parent"]]
    return tot, s
ch = {c: [cpath(r, c)[0] for r in croots] for c in ("TT", "FF")}
chs = [cpath(r, "TT")[1] for r in croots]
# per-column leaf spread (ideal) + channel spread
yspread = {c: round(max(lt_[c]) - min(lt_[c]), 3) for c in lt_}
cspread = {c: round(max(ch[c]) - min(ch[c]), 3) for c in ch}
ins = {c: round(max(ch[c]) + max(lt_[c]), 1) for c in ch}
# cell counts: groups = internal nodes + repeaters (nseg-1 per edge); x 12 columns
def ncells(ns):
    g = sum(1 for n in ns if n["kids"]) + sum(n["nseg"] - 1 for n in ns if n.get("parent"))
    return g
col_groups = ncells(per_col) + 0      # leaves = column-tap cells (merged with column trees, as r12)
ch_groups = ncells([n for n in cn if n not in croots]) + sum(r["nseg"] - 1 for r in croots if r.get("parent"))
# channel track need: max number of channel x-tree legs overlapping any x
ivs = []
for n in cn:
    if n.get("parent"):
        p = cby[n["parent"]]; ivs.append((min(p["xy"][0], n["xy"][0]), max(p["xy"][0], n["xy"][0])))
xs2 = np.linspace(0, W, 3000)
ov = int(max(sum(1 for a_, b_ in ivs if a_ <= x <= b_) for x in xs2))
# ---------------- identity gate on the ideal periodic geometry (translate the column template by PER*k)
def cells_of(ns):
    out = []
    byn = {n["tag"]: n for n in ns}
    for n in ns:
        if n["kids"] or not n.get("parent"):
            out.append(("node", n["xy"]))
        if n.get("parent"):
            p = byn[n["parent"]]["xy"]
            for k in range(1, n["nseg"]):
                out.append(("rep", (p[0] + (n["xy"][0] - p[0]) * k / n["nseg"], p[1] + (n["xy"][1] - p[1]) * k / n["nseg"])))
    return out
tmpl = cells_of(per_col)
pby = defaultdict(list)
for n in P.parts:
    pby[P.parts[n]["type"]].append(n)
def host(x, y):
    for n, (x0, y0, x1, y1) in rects.items():
        if x0 - 1e-6 <= x < x1 - 1e-6 and y0 - 1e-6 <= y < y1 - 1e-6:
            return n
    return None
def frame(n, x, y):
    x0, y0, x1, y1 = rects[n]; o = P.parts[n].get("orient", "R0")
    fx = (x1 - x) if o in ("MY", "R180") else (x - x0)
    fy = (y1 - y) if o in ("MX", "R180") else (y - y0)
    return (round(fx, 2), round(fy, 2))
use = defaultdict(lambda: defaultdict(list))
nohost = 0; core_hits = 0
for k in range(12):
    dx = trunk[k] - x0t
    for kind, (x, y) in tmpl:
        hn = host(x + dx, y)
        if hn is None:
            nohost += 1; continue
        use[P.parts[hn]["type"]][hn].append(frame(hn, x + dx, y))
viol = {}
for t, d in use.items():
    sets = [tuple(sorted(v)) for v in d.values()]
    full = len(pby[t])
    if len(set(sets)) > 1 or len(d) != full:
        ss = sorted(set(sets), key=len); diff = sorted(set(ss[0]) ^ set(ss[-1]))[:6]
        viol[t] = dict(instances=full, hosting=len(d), distinct_sets=len(set(sets)), counts=sorted(len(s) for s in sets), diff=diff,
                       orients={o: sorted({tuple(sorted(v)) == ss[0] for n, v in d.items() if P.parts[n].get("orient", "R0") == o}) for o in ("R0", "MX")})
# core conflicts of template sites (ISL clearance) -> slot snapping needed
inc = lambda q: any(c[0] - 1.08 < q[0] < c[2] + 1.08 and c[1] - 1.08 < q[1] < c[3] + 1.08 for c in cores)
for k in range(12):
    dx = trunk[k] - x0t
    core_hits += sum(1 for kind, (x, y) in tmpl if inc((x + dx, y)))
R["ab"] = dict(trunk_cols=trunk, period_um=PER, col_offsets_um=OFF, local_rows=[round(v, 2) for v in loc_rows],
               leaves_per_col=len(leaves), leaf_stage_hist=dict(stages), col_ideal_leaf_spread_ps=yspread,
               chan_ideal_spread_ps=cspread, chan_stages=sorted(set(chs)), chan_overlap_legs_max=ov,
               insertion_root_to_tap_ps=ins, groups_per_col=col_groups, groups_cols_total=12 * col_groups, groups_channel=ch_groups,
               identity=dict(types_hosting=len(use), violations=viol, nohost=nohost, template_sites_on_core_ISL=core_hits),
               max_leg_um=round(max(n["leg"] / n["nseg"] for n in per_col + cn if n.get("parent")), 2))
Path = Q3.Path
Path(out).write_text(json.dumps(R, indent=1))
print(json.dumps(R, indent=1)[:6000])
# cross-check: the channel x-tree cells placed IN the partitions next to the centre seam instead of a channel
chc = cells_of([n for n in cn])
alt = {}
for side, dy_ in (("below", -8.64), ("above", 8.64)):
    u2 = defaultdict(lambda: defaultdict(list))
    for kind, (x, y) in chc:
        hn = host(x, y + dy_)
        if hn: u2[P.parts[hn]["type"]][hn].append(frame(hn, x, y + dy_))
    bad = [t for t, d in u2.items() if len({tuple(sorted(v)) for v in d.values()}) > 1 or len(d) != len(pby[t])]
    alt[side] = dict(types_hosting=len(u2), types_violating=len(bad), examples=bad[:6])
R["ab"]["channel_cells_in_partitions_instead"] = alt
R["ab"]["channel_cells"] = len(chc)
Path(out).write_text(json.dumps(R, indent=1))
print("ALT", json.dumps(alt), len(chc))
