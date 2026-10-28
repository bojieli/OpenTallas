#!/usr/bin/env python3
"""INFRA-FIRST-QC-R35 (12.13f narrowed scope): M8/M9 row reservation for the QC PER-SLICE clock form.

COORD QC-R34 ruling (A) + QC-SLICECLK-2 ruling (b): reserve die-level clock tracks per tree CLASS so no class ever needs
to escape into another class's pin window (the R34 root cause: M8 PG stripe every 4.32 um, every gap inside some
slot-row window).  Form (QC-SLICECLK-2 README sec 2): ONE shared horizontal top spine along the sl band (1-D balanced
tree to 13 region roots) + per slice a full-height spine column (M9) with an equal y-bisection to 16 strips + one
horizontal leg per strip to the strip centre; local bisection inside the strip is the LOCAL class.

Geometry basis (die.pg.grid of the plan): M8/M9 0.48 @ 8.64, offset 4.32, nets VDD,VSS -> stripe centres every 4.32,
VDD at 4.32 + 8.64k, VSS at 8.64k (die_trial.pg_stripes).  Unit of reservation = a PAIR-ROW m (M8, y) or PAIR-COL m
(M9, x): the 8.64-um period centred on the VSS stripe at 8.64*m, bounded by the two VDD stripes.  It holds two 16w
tracks at VSS +-1.16 (on the 0.08 track grid, offset 0.04): near side shielded by the VSS stripe (flank), far side by a
drawn 0.64 VSS shield at VSS +-2.30 (tied by VIA89 to the crossing VSS grid).

usage: qc_slice_rows.py PLAN.json REGIONS.json TOOLS_DIE_PLAN_DIR OUT.json
All numbers printed here are OWN (UNCHECKED) unless an independent check is recorded.
"""
import json, sys, math, collections
from pathlib import Path

plan_path, reg_path, tools, out_path = sys.argv[1:5]
sys.path.insert(0, tools)
import schema as S, die_trial as DT  # noqa: E402

P = S.Plan(S.load(plan_path), Path(plan_path))
R = json.load(open(reg_path))["part_region"]
site = DT.SiteMap(P)
PITCH = 8.64
TRK = 1.16           # trunk centre offset from the VSS stripe centre (0.04 + 14 * 0.08)
SH = 2.30            # far drawn shield centre offset (TRK + 0.32 + 0.5 + 0.32)
W16, SP16 = 0.64, 0.5
RISER = 2.5          # die_clock_128.STACK_RISER_MAX_UM
JOG = 8.64           # TrackRouter max_move (M8 jog from a Y/A bar to an M9 track)
REACH = 448.524      # QC clock export reach (R32-R34)
H, Wd = P.H, P.W
assert abs(H / PITCH - round(H / PITCH)) < 1e-6
NH = round(H / PITCH)                     # 3040 pair-rows
assert NH % 32 == 0, NH                   # 16 strips x 2 -> every bisection node on a VSS row


# ------------------------------------------------------------------ legality (die_trial.SiteMap rules, analytic)
def legal_iv_row(y, xlo, xhi):
    ivs = sorted([max(a + 0.5, xlo), min(c - 0.5, xhi)] for (a, b, c, d) in site.parts if b + 0.5 <= y <= d - 0.5)
    m = []
    for v in ivs:
        if v[1] <= v[0]:
            continue
        if m and v[0] <= m[-1][1] + 1e-9:
            m[-1][1] = max(m[-1][1], v[1])
        else:
            m.append(list(v))
    cuts = sorted((r[0], r[2]) for r in site.forb if r[1] < y < r[3])
    out = []
    for a, b in m:
        segs = [[a, b]]
        for c0, c1 in cuts:
            ns = []
            for s0, s1 in segs:
                if c1 <= s0 or c0 >= s1:
                    ns.append([s0, s1]); continue
                if c0 > s0: ns.append([s0, c0])
                if c1 < s1: ns.append([c1, s1])
            segs = ns
        out += [s for s in segs if s[1] - s[0] >= 1.62]          # room for a BUFx24
    return out


def maxgap(ivs, lo, hi):
    g, cur = 0.0, lo
    for a, b in sorted(ivs):
        if b <= lo or a >= hi:
            continue
        g = max(g, a - cur); cur = max(cur, b)
    return max(g, hi - cur)


def col_free(x0, x1):
    """x intervals inside [x0, x1] not covered by any hard-core (+halo) rect at ANY y (full-height legal columns)."""
    f = sorted((a, c) for (a, b, c, d, k) in site.forb if a < x1 and c > x0)
    free, cur = [], x0
    for a, c in f:
        if a > cur: free.append((cur, a))
        cur = max(cur, c)
    if cur < x1: free.append((cur, x1))
    seams = sorted({v for (a, b, c, d) in site.parts for v in (a, c) if x0 < v < x1})
    out = []
    for a, b in free:                     # split at vertical partition seams (+-0.5 in_part margin)
        pts = [a] + [v for s in seams if a < s < b for v in (s - 0.5, s + 0.5)] + [b]
        out += [(round(pts[i], 3), round(pts[i + 1], 3)) for i in range(0, len(pts), 2) if pts[i + 1] - pts[i] > 1.0]
    return out


# ------------------------------------------------------------------ regions
box = collections.defaultdict(lambda: [1e18, 1e18, -1e18, -1e18])
for n, p in P.parts.items():
    r = R.get(n)
    if r is None:
        continue
    w, h = P.types[p["type"]]["outline_um"]; ox, oy = p["origin_um"]
    b = box[r]; b[:] = [min(b[0], ox), min(b[1], oy), max(b[2], ox + w), max(b[3], oy + h)]
XC = 16390.08                               # W0 | E0 boundary (die column centre of the slice array)
assert abs(XC / PITCH - round(XC / PITCH)) < 1e-6
MC = round(XC / PITCH)                      # 1897
SLW = 2471.04                               # slice pitch = 286 * 8.64
slices = []
for r, b in box.items():
    if not r.startswith("std_bg") and r != "hard_io_serdes_2":
        continue
    x0 = 1563.84 if r == "hard_io_serdes_2" else b[0]       # W5 slice = serdes region minus the west IO strip
    k = round((x0 - XC) / SLW)
    name = (f"E{k}" if k >= 0 else f"W{-k - 1}")
    slices.append(dict(region=r, name=name, k=k, x0=x0, x1=b[2], cb=(x0 + b[2]) / 2, E=k >= 0))
slices.sort(key=lambda s: s["x0"])
assert len(slices) == 12, [s["name"] for s in slices]

# spine column per slice: E0 pair-cols 2117..2120 (x 18,290.88 .. 18,316.80, inside the E0 full-height legal column
# 18,239.5 .. 18,322.8, QC-SLICECLK-2's x ~ 18,315), E_k = +286 k, W mirrored about XC (m' = 2*MC - m)
E0_COLS = [2117, 2118, 2119, 2120]
for s in slices:
    k = s["k"]
    cols = [m + 286 * k for m in E0_COLS] if s["E"] else sorted(2 * MC - (m + 286 * (-k - 1)) for m in E0_COLS)
    s["cols"] = cols
    s["x_s"] = round(PITCH * (cols[0] + cols[-1]) / 2, 3)
    s["legal_col"] = [iv for iv in col_free(s["x0"], s["x1"]) if iv[0] - JOG <= PITCH * cols[0] and PITCH * cols[-1] <= iv[1] + JOG + 30]
HUB = [r for r in box if r.startswith("hard_ucie")][0]
HUB_X = round(PITCH * 135, 3)               # 1166.4: HUB tap + source feed column (coll_core 777.6..1563.84)

# ------------------------------------------------------------------ class reservations
M_ROOT = NH // 2                            # 1520: slice root row (y = H/2, the plan spine root y 13,132.8)
TOP_ROWS = {"T3_tap": M_ROOT, "T2": M_ROOT + 1, "T1": M_ROOT + 2, "T0_root": M_ROOT + 3, "FEED": M_ROOT + 4,
            "SPARE": M_ROOT + 5}
COL_ROOT_JOG = M_ROOT - 1                   # root Y jog row, column band only
strip = NH // 16                            # 190 pair-rows per strip
LEVEL_ROWS = {1: [NH // 4, 3 * NH // 4]}
LEVEL_ROWS[2] = [NH // 8 * j for j in (1, 3, 5, 7)]
LEVEL_ROWS[3] = [strip * j for j in range(1, 16, 2)]
LEVEL_ROWS[4] = [strip // 2 + strip * i for i in range(16)]       # leg rows (strip centres)

# 1-D balanced top tree over the 13 taps (QC-SLICECLK-2 'balanced 1-D tree'; SLICECLK-3 owns the real build)
taps = sorted([HUB_X] + [s["x_s"] for s in slices])


def build1d(xs, depth=0, acc=None):
    acc = [] if acc is None else acc
    if len(xs) == 1:
        return xs[0], acc
    h = (len(xs) + 1) // 2
    a, _ = build1d(xs[:h], depth + 1, acc); b, _ = build1d(xs[h:], depth + 1, acc)
    node = (a + b) / 2
    acc.append(dict(depth=depth, node=node, span=(min(a, b), max(a, b))))
    return node, acc


root_x, nets = build1d(taps)
maxd = max(n["depth"] for n in nets)
assert maxd <= 3, maxd
row_of_depth = {0: TOP_ROWS["T0_root"], 1: TOP_ROWS["T1"], 2: TOP_ROWS["T2"], 3: TOP_ROWS["T3_tap"]}

res = []                                    # (layer, m, lo, hi, cls, role)
for n in nets:
    # taps reached at depth < 3 get pass-through stages down to the T3 row (equal stage count), same x span
    res.append(("M8", row_of_depth[n["depth"]], n["span"][0], n["span"][1], "TOP", f"d{n['depth']}"))
res.append(("M8", TOP_ROWS["FEED"], HUB_X, root_x, "TOP", "feed"))
res.append(("M8", TOP_ROWS["SPARE"], HUB_X, max(taps), "TOP", "spare"))
res.append(("M9", 135, PITCH * (8432.64 // PITCH), PITCH * TOP_ROWS["FEED"], "TOP", "hub_feed_column"))
for s in slices:
    xb0, xb1 = PITCH * s["cols"][0] - PITCH / 2, PITCH * s["cols"][-1] + PITCH / 2
    for m in s["cols"]:
        res.append(("M9", m, 0.0, H, f"COL:{s['name']}", "column"))
    res.append(("M8", COL_ROOT_JOG, xb0 - JOG, xb1 + JOG, f"COL:{s['name']}", "root_jog"))
    for lv in (1, 2, 3):
        for m in LEVEL_ROWS[lv]:
            res.append(("M8", m, xb0 - JOG, xb1 + JOG, f"COL:{s['name']}", f"node_L{lv}"))
    for i, m in enumerate(LEVEL_ROWS[4]):
        # leg: from the column node to the strip centre (c-column boundary cb), on the strip centre row
        lo, hi = (s["cb"], xb1 + JOG) if s["E"] else (xb0 - JOG, s["cb"])
        res.append(("M8", m, lo, hi, f"COL:{s['name']}", f"leg{i}"))

# ------------------------------------------------------------------ checks
chk = collections.OrderedDict()
# (1) class exclusivity + demand <= supply per pair-row / pair-col
by = collections.defaultdict(list)
for r in res:
    by[(r[0], r[1])].append(r)
conflicts = []
for key, rs in by.items():
    pts = sorted({v for r in rs for v in (r[2], r[3])})
    for a, b in zip(pts, pts[1:]):
        mid = (a + b) / 2
        here = [r for r in rs if r[2] <= mid <= r[3]]
        cls = {r[4] for r in here}
        if len(cls) > 1:
            conflicts.append(dict(layer=key[0], m=key[1], x=[a, b], classes=sorted(cls)))
col_conc = 0
for lv_y in [y * 0.5 for y in range(0, 2 * NH + 1, 7)]:
    c = 0
    for lv, rows in ((1, [NH // 2]), (2, LEVEL_ROWS[1]), (3, LEVEL_ROWS[2]), (4, LEVEL_ROWS[3])):
        half = NH // (2 ** (lv + 1))
        c += any(abs(lv_y - r) <= half for r in rows)
    col_conc = max(col_conc, c)
chk["class_conflicts"] = conflicts
chk["demand_supply"] = dict(
    top_rows=dict(rows=len(TOP_ROWS), tracks_per_row=2, max_nets_per_row=max(
        sum(1 for n in nets if row_of_depth[n["depth"]] == m and n["span"][0] <= x <= n["span"][1])
        for m in row_of_depth.values() for x in [t + 1 for t in taps] + [n["node"] for n in nets]),
        plus_root_jog_in_column_band=1),
    column=dict(pair_cols=4, tracks=8, max_concurrent_levels=col_conc, root_feed="M8 jog (row 1519), no M9 track"),
    node_rows=dict(tracks=2, demand=2, note="A drop jog + Y jog of one bisection node"),
    leg_rows=dict(tracks=2, demand="1 trunk + the L4 node A jog inside the column band; flow-oriented (MY) repeaters "
                  "or repeaters outside the column band keep the escape track free"),
    top_tree=dict(taps=len(taps), depth=maxd + 1, root_x=round(root_x, 2), tap_x=[round(t, 2) for t in taps]))

# (2) pin-window access (VIA78 risers <= 2.5 um; VIA89 jogs <= 8.64 um) on legal sites
acc = []
top_lo, top_hi = 778.1, max(taps) + 10
for name, m in TOP_ROWS.items():
    y = PITCH * m
    g = max(maxgap(legal_iv_row(y + dy, top_lo, top_hi), top_lo, top_hi) for dy in (-TRK, TRK))
    acc.append(dict(cls="TOP", row=m, y=round(y, 2), max_illegal_gap_um=round(g, 2), ok=g <= 2.0))
for s in slices:
    xs = [PITCH * m + d for m in s["cols"] for d in (-TRK, TRK)]
    ok_cols = [x for x in xs if any(a - JOG <= x <= b + JOG for a, b in s["legal_col"] if b - a > 5)]
    acc.append(dict(cls=f"COL:{s['name']}", tracks_x=[round(x, 2) for x in xs], legal_col=s["legal_col"],
                    tracks_reachable=len(ok_cols), ok=len(ok_cols) == len(xs)))
    legs = []
    for i, m in enumerate(LEVEL_ROWS[4]):
        y = PITCH * m
        lo, hi = sorted((s["cb"], s["x_s"]))
        ivs = [iv for iv in legal_iv_row(y + TRK, lo - 80, hi + 80)]
        g = maxgap(ivs, lo + (75 if s["E"] else 0), hi - (0 if s["E"] else 75))
        legs.append(round(g, 1))
    acc.append(dict(cls=f"LEG:{s['name']}", leg_len_um=round(abs(s["x_s"] - s["cb"]), 2),
                    max_unrepeatable_span_per_strip=legs, over_reach=[i for i, g in enumerate(legs) if g > REACH]))
chk["pin_access"] = acc
# (3) shield adjacency (geometry of one pair-row; same for M9 with 0.48 or 0.672 stripes)
sh = {}
for lay, wpg in (("M8 0.48", 0.48), ("M9 0.48", 0.48), ("M9 0.672 (QC event M9 .672)", 0.672)):
    near = TRK - W16 / 2 - wpg / 2                       # clock edge -> VSS stripe edge
    far = (PITCH / 2 - wpg / 2) - (SH + W16 / 2)          # drawn far shield edge -> VDD stripe edge
    sh[lay] = dict(clock_to_vss_stripe_edge=round(near, 3), min_space=SP16, flank_max=SP16 + W16,
                   far_shield_to_vdd_edge=round(far, 3), ok=SP16 - 1e-9 <= near <= SP16 + W16 and far >= SP16)
chk["shield"] = sh
# (4) wire inventory for the IR / power estimate
L_top = sum(n["span"][1] - n["span"][0] for n in nets) + (root_x - HUB_X) + (PITCH * TOP_ROWS["FEED"] - 8432.64)
L_col = (H / 2) + 2 * (H / 4) + 4 * (H / 8) + 8 * (H / 16)   # L1..L4 net lengths per slice (equal bisection)
L_leg = 16 * sum(abs(s["x_s"] - s["cb"]) for s in slices) / len(slices)
chk["wire_mm"] = dict(top=round(L_top / 1e3, 1), column_per_slice=round(L_col / 1e3, 2), legs_per_slice=round(L_leg / 1e3, 2),
                      total=round((L_top + 12 * (L_col + L_leg)) / 1e3, 1))

out = dict(schema="qc_slice_clock_rows/1", lane="INFRA-FIRST-QC-R35", consumer="QC-SLICECLK-3",
           basis=dict(plan="results/qc_sliceclk_1027/plan/die_plan_sliceclk.json.gz (claude/qc-sliceclk-1027@88bc183c7c)",
                      regions="results/qc_sliceclk_1027/plan/regions.json", pg_grid=P.die["pg"]["grid"],
                      die_um=[Wd, H]),
           unit=dict(pair_row="M8: y in [8.64m - 4.32, 8.64m + 4.32] (VSS stripe at 8.64m, VDD stripes at the edges)",
                     pair_col="M9: same in x", tracks=f"VSS +-{TRK} (16w 0.64, on the 0.04+0.08n track grid)",
                     shields=f"near = the VSS stripe (flank); far = drawn 0.64 VSS at VSS +-{SH}, VIA89-tied to the crossing VSS grid",
                     pin_window=f"cells of a class put their pin row within {RISER} um of their trunk (VIA78 riser) or reach an M9 track by an M8 jog <= {JOG} um"),
           rules=["A pair-row/pair-col reserved for a class over an x (y) span carries only that class's trunks, jogs, "
                  "escapes and drawn shields over that span; no other class's M8/M9 shape and no other class's "
                  "M8-access pin window (+-2.5 um of a track) inside it.",
                  "LOCAL (strip-local bisection, core feeds, reset, anything else on M8/M9) uses every other pair-row/"
                  "pair-col; its column-band M8 jogs avoid the reserved node rows.",
                  "Column-chain repeaters sit at any y in the legal column except the TOP rows 1519..1525 and the "
                  "node/leg rows; their in/out jogs are on opposite sides of the pin row (vertical chains need no escape).",
                  "Horizontal repeaters (TOP, legs): flow-oriented (MY for -x flow) or the row's second track as escape.",
                  "No PG stripe is cut, moved or narrowed (the plan die.pg.grid is unchanged)."],
           top=dict(rows={k: dict(m=v, y=round(PITCH * v, 2)) for k, v in TOP_ROWS.items()}, x_span=[HUB_X, max(taps)],
                    root_jog_row=dict(m=COL_ROOT_JOG, y=round(PITCH * COL_ROOT_JOG, 2), scope="column bands only"),
                    hub_feed_col=dict(m=135, x=HUB_X, y=[8432.64, round(PITCH * TOP_ROWS['FEED'], 2)]),
                    taps=[dict(region=HUB, x=HUB_X)] + [dict(region=s["region"], slice=s["name"], x=s["x_s"]) for s in slices],
                    nets_1d=[dict(depth=n["depth"], row=row_of_depth[n["depth"]], node_x=round(n["node"], 2),
                                  span=[round(n["span"][0], 2), round(n["span"][1], 2)]) for n in nets]),
           slices=[dict(slice=s["name"], region=s["region"], x_range=[s["x0"], s["x1"]], cb=s["cb"],
                        spine_x=s["x_s"], pair_cols=s["cols"], track_x=[round(PITCH * m + d, 2) for m in s["cols"] for d in (-TRK, TRK)],
                        legal_column=s["legal_col"],
                        node_rows={f"L{lv}": [dict(m=m, y=round(PITCH * m, 2)) for m in LEVEL_ROWS[lv]] for lv in (1, 2, 3)},
                        root=dict(m=M_ROOT, y=round(PITCH * M_ROOT, 2)),
                        leg_rows=[dict(strip=i, m=m, y=round(PITCH * m, 2),
                                       x=sorted([round(s["cb"], 2), round(s["x_s"], 2)])) for i, m in enumerate(LEVEL_ROWS[4])])
                   for s in slices],
           reservations=[dict(layer=r[0], m=r[1], centre_um=round(PITCH * r[1], 2), lo=round(r[2], 2), hi=round(r[3], 2),
                              cls=r[4], role=r[5]) for r in res],
           checks=chk)
json.dump(out, open(out_path, "w"), indent=1)
print(json.dumps(dict(checks=dict((k, v) for k, v in chk.items() if k != "pin_access"),
                      pin_access_fail=[a for a in acc if not a.get("ok", True) or a.get("over_reach")]), indent=1)[:6000])
