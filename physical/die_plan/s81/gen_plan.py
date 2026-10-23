#!/usr/bin/env python3
"""PLAN-S81: generate the S81 (DeepSeek ROM, 72-frame MU release) die plan (TOPDOWN-PLAN, owner-approved 2026-10-23).

Inputs (as-built connectivity, read-only):
  --asbuilt  cap30 gen-main plan.json (ot-gold2:/srv/opentallas-scratch/claude/stw-s81c-cap30/gen-main/plan.json):
             blocks (masters, outlines) + 835 data links (endpoints, widths).
  --census   FT-TOOL census lanes tsv (s81_lanes.tsv): adds the ctl groups (reset/clock dropped: per-partition sync).
Output: die_plan.json (schema opentallas.die_plan.v1, tools/die_plan/README.md), stats.json, render png.

Plan decisions (v1, see README.md next to this file):
  * Frames -> 3 band partitions (one clock region each = the as-built r0/r1/r2 regions), one band outline for h9/h10.
  * Frame arrays 6 x 6 per side; every row = 2 E-W chains of 3 frames (head A at the centre side).  x is a broadcast
    (slice xc = 4 copies of xw4), so a 6-frame slice half needs ONE x lane (A6 forwards a copy to the W chain head);
    ret shifts back through the chain (C -> B -> A).  Only b0 bands carry chain/ft logic; b1/b2 are position-free.
  * S slice halves in the lower band, N halves in the upper band (xring S/N rings become neighbour links).
  * Centre: lane columns (ft partitions) beside each array; svc 2 x 8; B0 = irg + phy + ctrl/etap tiles; B4 = units.
"""
import argparse
import collections
import csv
import heapq
import json
import math
from pathlib import Path

G = 8.64
REACH = 1500.0
PINS_PER_UM = 5.0   # router capacity (G0 limit 6 incl. epoch bits + gaps)
DIE = (33000.0, 26000.0)
X0 = 12 * G          # 103.68: first grid line inside the 100-um seal ring
YTOP = 2997 * G      # 25894.08: last grid line under the seal ring
BW, BH = 167 * G, 142 * G          # frame band 1442.88 x 1226.88 (h10 band 1224 -> grid; h9 band 1123.2 padded)
FH = 3 * BH                        # frame 3680.64
NCOL, NROW = 6, 6
SER_W, SER_H = 445 * G, 60 * G     # serdes re-aspected to a row slot 3844.8 x 518.4 (rework, PHY model)
LANE_W = 118 * G                   # 1019.52 lane column
SVC_W, SVC_H = 200 * G, 440 * G    # 1728 x 3801.6
SL_H = 805 * G                     # 6955.2 slice band
IRG_W, IRG_H = 120 * G, 140 * G    # 1036.8 x 1209.6
HARD_KINDS = ("phy", "link")
MIRROR = False


def snap(v):
    return round(v / G) * G


class Part:
    def __init__(self, name, base, x0, y0, w, h, orient="R0", contents=None, kind="", note=""):
        # v1: no mirrored replicas.  With partition outlines on the 8.64 grid, a MY/MX copy puts N/S (E/W) pins
        # off the M5/M7 (M4/M6) tracks in its own frame (track offsets are not mirror-symmetric), so mirrored
        # instances become their own types anyway (PLAN-TOOL G0 'identical pin table').
        orient = "R0" if not MIRROR else orient
        self.name, self.base, self.orient, self.kind, self.note = name, base, orient, kind, note
        self.x0, self.y0, self.w, self.h = snap(x0), snap(y0), snap(w), snap(h)
        self.contents = contents or []
        self.slots = []        # ft slots (dicts)
        self.buses = []        # functional buses (dicts)

    @property
    def x1(self):
        return self.x0 + self.w

    @property
    def y1(self):
        return self.y0 + self.h

    def c(self):
        return (self.x0 + self.w / 2, self.y0 + self.h / 2)


# ------------------------------------------------------------------------------------------------- floorplan
def build_floorplan(ab, y_arr, flips):
    """Return (parts, frame_slots, channels).  frame_slots[(side,row,col)] = [b0,b1,b2] parts."""
    parts, chans = [], []
    blk = {b["name"]: b for b in ab["blocks"]}
    xW0, xW1 = X0, X0 + NCOL * BW                          # W array
    xLW1 = xW1 + LANE_W                                    # W lane column
    widths = {}
    S = ["s_%dS" % k for k in range(8)]
    N = ["s_%dN" % k for k in range(8)]
    for k in range(8):
        widths[k] = snap(max(blk[S[k]]["w"], blk[N[k]]["w"]))
    xs = [xLW1]
    for k in range(8):
        xs.append(xs[-1] + widths[k])
    xLE0 = xs[-1]
    xE0 = xLE0 + LANE_W
    xE1 = xE0 + NCOL * BW
    assert xE1 <= DIE[0] - 100 + 1e-6, xE1
    # --- centre bands
    yB0 = X0
    yS0 = yB0 + 2 * IRG_H                 # svc band
    yL0 = yS0 + 2 * SVC_H                 # lower slice band (S halves)
    yU0 = yL0 + SL_H                      # upper slice band (N halves)
    yT0 = yU0 + SL_H                      # top band
    assert yT0 < YTOP
    cx = (xLW1 + xLE0) / 2
    xsv0 = snap(cx - 4 * SVC_W)           # svc/B0 band x range (wider than the slice core)
    xsv1 = xsv0 + 8 * SVC_W
    # slices
    for k in range(8):
        for nm, y in ((S[k], yL0), (N[k], yU0)):
            b = blk[nm]
            parts.append(Part(nm, b["master"], xs[k], y, widths[k], SL_H, "R0" if k < 4 else "MY",
                              [dict(inst="u_" + nm, module=b["master"], kind="slice")], kind="slice"))
    # svc 2 x 8: column k = (rsv_2k lower, rsv_2k+1 upper) as built
    for k in range(8):
        for j in range(2):
            nm = "rsv_%02d" % (2 * k + j)
            b = blk[nm]
            parts.append(Part(nm, b["master"] + ("_lo" if j == 0 else "_up"), xsv0 + k * SVC_W, yS0 + j * SVC_H,
                              SVC_W, SVC_H, "R0" if k < 4 else "MY",
                              [dict(inst="u_" + nm, module=b["master"], kind="svc")], kind="svc"))
    # B0: irg 2x2 W | phy + ctrl/etap tiles (432-um slots on the svc quarter-column grid) | irg 2x2 E
    IRS = 300 * G          # irg stack slot 2592 = 1.5 svc columns (2 x 1036.8 irg inside)
    irgW = [("irg_01", "irg_00"), ("irg_02", "irg_03")]
    irgE = [("irg_05", "irg_04"), ("irg_06", "irg_07")]
    for i, col in enumerate(irgW):
        for j, nm in enumerate(col):
            parts.append(Part(nm, "dsdv_idx_rg3", xsv0 + i * IRS / 2, yB0 + j * IRG_H, IRS / 2, IRG_H, "R0",
                              [dict(inst="u_" + nm, module="dsdv_idx_rg3", kind="idx")], kind="idx"))
    for i, col in enumerate(irgE):
        for j, nm in enumerate(col):
            parts.append(Part(nm, "dsdv_idx_rg3", xsv1 - (2 - i) * IRS / 2, yB0 + j * IRG_H, IRS / 2, IRG_H, "MY",
                              [dict(inst="u_" + nm, module="dsdv_idx_rg3", kind="idx")], kind="idx"))
    xm0, xm1 = xsv0 + IRS, xsv1 - IRS
    phy_h = IRG_H
    parts.append(Part("phy_hbm", "ot_hbm3e_phy_v41x_aw30_e8p5", xm0, yB0, xm1 - xm0, phy_h, "R0",
                      [dict(inst="u_phy_hbm", module="ot_hbm3e_phy_v41x_aw30_e8p5", kind="phy")], kind="phy",
                      note="hard PHY 8500 x 1177 inside the snapped slot"))
    cte_w = 125 * G    # 1080 (8 x 1080 = the 8640 phy-width row): one ctrl pair (ctrl_2c, ctrl_2c+1 + their etaps) per svc column c
    cte_h = (yS0 - yB0) - phy_h
    nsl = int(round((xm1 - xm0) / cte_w))
    want = [round((1728 * c + 864 - IRS - 432) / 864) for c in range(8)]
    left = []
    for c in range(8):
        left.append(max(want[c], (left[-1] + 1) if left else 0))
    for c in range(7, -1, -1):
        lim = (nsl - 1) if c == 7 else left[c + 1] - 1
        left[c] = min(left[c], lim)
    for c in range(8):
        sl = left[c]
        cont = []
        for k in (2 * c, 2 * c + 1):
            cont += [dict(inst="u_ctrl_%02d" % k, module="dsfd_ctrl_rg3_native32", kind="ctrl"),
                     dict(inst="u_etap_%02d" % k, module="dsdv_eng_tap_w" if k == 0 else "dsdv_eng_tap", kind="unit")]
        parts.append(Part("cte_c%d" % c, "cte2" + ("_w" if c == 0 else ""), xm0 + sl * cte_w, yB0 + phy_h, cte_w,
                          cte_h, "R0", cont, kind="cte"))
    for sl in range(nsl):
        if sl not in left:
            chans.append(dict(rect_um=[xm0 + sl * cte_w, yB0 + phy_h, xm0 + (sl + 1) * cte_w, yS0],
                              reason="v1 slack slot in the ctrl row (ctrl pairs sit under their svc column)"))
    # top band B4: units in slice-column slots (abut the slices they serve)
    top = {0: ("bk_sel", "dsfd_bk_selector_vm"), 1: ("bk_col", "dsfd_bk_collector"),
           2: ("seqhost", "dsdv_seq_host_mux"), 3: ("iqf", "dsdv_idx_qf"), 4: ("gunit", "dsdv_gunit"),
           7: ("eng", "dsdv_eng_rr")}
    for k in range(8):
        if k in top:
            nm, m = top[k]
            parts.append(Part(nm, m, xs[k], yT0, widths[k], YTOP - yT0, "R0", [dict(inst="u_" + nm, module=m, kind="unit")],
                              kind="unit", note=("re-aspected parent slot (rework)" if nm == "bk_sel" else "")))
        else:
            chans.append(dict(rect_um=[xs[k], yT0, xs[k] + widths[k], YTOP],
                              reason="v1 slack top-band slot (no unit for this slice column)"))
    # lane columns: segments <= reach tall; narrower beside the svc/B0 band
    def lane_col(side, xa, xb, xa2, xb2):
        ys = []
        y = X0
        # segment boundaries = frame band edges (pins line up with the array) + the svc/slice band edge
        bnds = sorted({X0, YTOP, yL0} | {y_arr + i * BH for i in range(3 * NROW + 1)})
        bnds = [b for b in bnds if X0 <= b <= YTOP]
        keep = [bnds[0]]
        for b in bnds[1:]:
            if b - keep[-1] < 300 and b not in (yL0, YTOP):
                continue
            if b - keep[-1] < 300 and keep[-1] not in (X0, yL0):
                keep[-1] = b
                continue
            keep.append(b)
        bnds = [keep[0]]
        for a, b in zip(keep, keep[1:]):
            n = max(1, math.ceil((b - a) / 1400.0))
            bnds += [snap(a + (b - a) * i / n) for i in range(1, n)] + [b]
        assert all(b - a <= REACH for a, b in zip(bnds, bnds[1:])), bnds
        for i, (a, b) in enumerate(zip(bnds, bnds[1:])):
            narrow = b <= yL0 + 1e-6
            x0, x1 = (xa2, xb2) if narrow else (xa, xb)
            parts.append(Part("lc%s_%02d" % (side, i), "lanecol", x0, a, x1 - x0, b - a,
                              "R0" if side == "W" else "MY", [], kind="lane"))
    lane_col("W", xW1, xLW1, xW1, xsv0)
    lane_col("E", xLE0, xE0, xsv1, xE0)
    # arrays + serdes rows
    fslots = {}
    for side, xa, orient in (("W", xW0, "R0"), ("E", xE0, "MY")):
        for r in range(NROW):
            fl = flips[side][r]
            for c in range(NCOL):
                # column index c counted from the centre side: c=0 is next to the lane column
                xcol = (xa + (NCOL - 1 - c) * BW) if side == "W" else (xa + c * BW)
                y = y_arr + r * FH
                bands = []
                for b in range(3):
                    yb = (y + b * BH) if not fl else (y + (2 - b) * BH)
                    o = orient if not fl else ("MX" if orient == "R0" else "R180")
                    p = Part("f%s_r%d_c%d_b%d" % (side, r, c, b), "fband", xcol, yb, BW, BH, o, [], kind="frame")
                    parts.append(p)
                    bands.append(p)
                fslots[(side, r, c)] = bands
        # serdes rows
        names = {"W": ([["lk_WS0"], ["lk_WS1"]], [["lk_WN0"], ["lk_WN2"], ["lk_WN1"], ["lk_WN3"]]),
                 "E": ([["lk_ES0"], ["lk_ES1"]], [["lk_EN0"], ["lk_EN1"]])}[side]
        xin = xW1 if side == "W" else xE0      # inner edge (touches the lane column)
        def row(nms, y):
            for i, nm in enumerate(nms):
                x = (xin - (i + 1) * SER_W) if side == "W" else (xin + i * SER_W)
                parts.append(Part(nm, "ot_pdie_serdes_row", x, y, SER_W, SER_H, orient,
                                  [dict(inst="u_" + nm, module="ot_pdie_serdes", kind="link")], kind="link",
                                  note="SerDes PHY model re-aspected to a row slot (rework)"))
            rest = NCOL * BW - len(nms) * SER_W
            xr = (X0 if side == "W" else xin + len(nms) * SER_W)
            chans.append(dict(rect_um=[xr, y, xr + rest, y + SER_H],
                              reason="serdes row remainder at the die edge (no logic needs it)"))
        for j, nms in enumerate(names[0]):
            row(nms, X0 + j * SER_H)
        ybot = X0 + len(names[0]) * SER_H
        assert y_arr >= ybot - 1e-6
        if y_arr > ybot + 1e-6:
            chans.append(dict(rect_um=[xa, ybot, xa + NCOL * BW, y_arr], reason="array vertical alignment slack"))
        yt = y_arr + NROW * FH
        for j, nms in enumerate(names[1]):
            row(nms, yt + j * SER_H)
        ytop = yt + len(names[1]) * SER_H
        if ytop < YTOP - 1e-6:
            chans.append(dict(rect_um=[xa, ytop, xa + NCOL * BW, YTOP], reason="array vertical alignment slack"))
    geo = dict(xs=xs, yB0=yB0, yS0=yS0, yL0=yL0, yU0=yU0, yT0=yT0, xsv0=xsv0, xsv1=xsv1, xLW1=xLW1, xLE0=xLE0,
               xW1=xW1, xE0=xE0)
    return parts, fslots, chans, geo


# ---------------------------------------------------------------------------------------------- adjacency
def shared_face(a, b, minlen=20.0):
    """face of a toward b and the overlap interval [lo,hi] along it, or None."""
    eps = 1e-3
    if abs(a.x1 - b.x0) < eps or abs(b.x1 - a.x0) < eps:
        lo, hi = max(a.y0, b.y0), min(a.y1, b.y1)
        if hi - lo >= minlen:
            return ("E" if abs(a.x1 - b.x0) < eps else "W"), lo, hi
    if abs(a.y1 - b.y0) < eps or abs(b.y1 - a.y0) < eps:
        lo, hi = max(a.x0, b.x0), min(a.x1, b.x1)
        if hi - lo >= minlen:
            return ("N" if abs(a.y1 - b.y0) < eps else "S"), lo, hi
    return None


def adjacency(parts):
    adj = collections.defaultdict(dict)
    srt = sorted(parts, key=lambda p: p.x0)
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            if a.x0 > b.x1 + 1 or b.x0 > a.x1 + 1 or a.y0 > b.y1 + 1 or b.y0 > a.y1 + 1:
                continue
            f = shared_face(a, b)
            if f:
                adj[a.name][b.name] = f
                opp = dict(N="S", S="N", E="W", W="E")[f[0]]
                adj[b.name][a.name] = (opp, f[1], f[2])
    return adj


# ------------------------------------------------------------------------------------------- logical links
def frame_mapping(ab):
    """slice half -> list of chains (each 3 as-built frame names, A,B,C; h10 frames at C)."""
    blk = {b["name"]: b for b in ab["blocks"]}
    srv = collections.defaultdict(list)
    for l in ab["links"]:
        if l["c"] == "ret":
            srv[ab["blocks"][l["e"][1][0]]["name"]].append(ab["blocks"][l["e"][0][0]]["name"])
    groups = {}
    for s, fr in srv.items():
        h10 = sorted(f for f in fr if blk[f]["master"] == "col_h10")
        h9 = sorted(f for f in fr if blk[f]["master"] != "col_h10")
        n = len(fr) // 3
        assert len(fr) % 3 == 0 and len(h10) in (0, n), (s, fr)
        chains = []
        for i in range(n):
            ab_ = h9[2 * i: 2 * i + 2] if h10 else h9[3 * i: 3 * i + 2]
            c = h10[i] if h10 else h9[3 * i + 2]
            chains.append(ab_ + [c])
        groups[s] = chains
    return groups


def row_plan():
    """side -> 6 rows: (band 'L'/'U', [slice halves]); 6-group rows hold 1 half, 3-group rows 2 halves."""
    plan = {}
    for side, ks in (("W", (0, 1, 2, 3)), ("E", (7, 6, 5, 4))):
        a, b, c, d = ks
        plan[side] = [("L", ["s_%dS" % c]), ("L", ["s_%dS" % a]), ("L", ["s_%dS" % b, "s_%dS" % d]),
                      ("U", ["s_%dN" % b, "s_%dN" % d]), ("U", ["s_%dN" % c]), ("U", ["s_%dN" % a])]
    return plan


FRAME_INTERNAL = [("r0", "r1", 1263), ("r1", "r2", 1229), ("r2", "r1", 384), ("r1", "r0", 141)]
XW, RW = 1104, 70


def logical_links(ab, census, fslots, groups, rplan):
    """List of logical lanes: dict(id, src=(part,bus), dst=(part,bus), width, kind, cls, path_hint)."""
    out = []
    blk2part = {}
    for b in ab["blocks"]:
        nm = b["name"]
        if b["kind"] == "frame":
            continue
        if nm.startswith("ctrl_") or nm.startswith("etap_"):
            blk2part[nm] = "cte_c%d" % (int(nm[5:]) // 2)
        else:
            blk2part[nm] = nm
    fmap = {}   # as-built frame -> (side,row,col)
    chains_meta = []
    for side, rows in rplan.items():
        for r, (band, halves) in enumerate(rows):
            if len(halves) == 1:
                ch = groups[halves[0]]
                assert len(ch) == 2
                spec = [(halves[0], ch[0], "6E"), (halves[0], ch[1], "6W")]
            else:
                spec = [(halves[0], groups[halves[0]][0], "3E"), (halves[1], groups[halves[1]][0], "3W")]
            for half, chain, pos in spec:
                cols = (0, 1, 2) if pos.endswith("E") else (3, 4, 5)
                for f, c in zip(chain, cols):
                    fmap[f] = (side, r, c)
                chains_meta.append(dict(side=side, row=r, half=half, chain=chain, cols=cols, kind=pos))
    # frame internal band links (every frame)
    for key, bands in fslots.items():
        nm = "%s_r%d_c%d" % key
        for a, b, w in FRAME_INTERNAL:
            ia, ib = int(a[1]), int(b[1])
            out.append(dict(id="fi_%s_%s%s" % (nm, a, b), src=(bands[ia].name, "%s%s_o" % (a, b)),
                            dst=(bands[ib].name, "%s%s_i" % (a, b)), width=w, kind="data", cls="frame_int"))
    # chain lanes
    for m in chains_meta:
        side, r, half = m["side"], m["row"], m["half"]
        b0 = [fslots[(side, r, c)][0].name for c in m["cols"]]
        inner = tuple(fslots[(side, r, c)][0].name for c in (0, 1, 2))
        tag = "%s_r%d_%s" % (side, r, m["kind"])
        if m["kind"] in ("6E", "3E", "3W"):
            # x from the slice half to head A (for 3W: through the E chain's b0 bands = ft)
            out.append(dict(id="x_" + tag, src=(half, "xc_%s" % tag), dst=(b0[0], "x_i"), width=XW, kind="data",
                            cls="x", allow=inner if m["kind"] == "3W" else ()))
        else:  # 6W: copy of x forwarded by the E chain head
            a_e = fslots[(side, r, 0)][0].name
            out.append(dict(id="x_" + tag, src=(a_e, "xs_o"), dst=(b0[0], "x_i"), width=XW, kind="data",
                            cls="x", allow=inner))
        out.append(dict(id="xo_%s_ab" % tag, src=(b0[0], "xo_o"), dst=(b0[1], "x_i"), width=XW, kind="data",
                        cls="xo"))
        out.append(dict(id="xo_%s_bc" % tag, src=(b0[1], "xo_o"), dst=(b0[2], "x_i"), width=XW, kind="data",
                        cls="xo"))
        out.append(dict(id="rt_%s_cb" % tag, src=(b0[2], "ret_o"), dst=(b0[1], "ret_i"), width=RW, kind="data",
                        cls="ret"))
        out.append(dict(id="rt_%s_ba" % tag, src=(b0[1], "ret_o"), dst=(b0[0], "ret_i"), width=2 * RW,
                        kind="data", cls="ret"))
        out.append(dict(id="rt_%s" % tag, src=(b0[0], "ret_o"), dst=(half, "rt_%s" % tag), width=3 * RW,
                        kind="data", cls="ret", allow=inner if m["kind"].endswith("W") else ()))
    # as-built non-frame links (plan.json data) + census ctl groups
    seen = set()
    for l in ab["links"]:
        if l["c"] in ("x_frame", "ret"):
            continue
        src = ab["blocks"][l["e"][0][0]]["name"]
        for k, e in enumerate(l["e"][1:]):
            dst = ab["blocks"][e[0]]["name"]
            ps, pd = blk2part[src], blk2part[dst]
            if ps == pd:
                continue
            lid = "%s%s" % (l["i"], "" if len(l["e"]) == 2 else "_%d" % k)
            out.append(dict(id=lid, src=(ps, l["e"][0][1] + "_" + l["i"]), dst=(pd, e[1] + "_" + l["i"]),
                            width=int(l["b"]), kind="data", cls=l["c"]))
            seen.add((src, dst, l["c"]))
    n_ctl = 0
    for row in census:
        if row["kind"] != "ctl":
            continue
        s, d = row["src"], row["dst"]
        if not (s.startswith("u_") and d.startswith("u_")):
            continue
        s, d = s[2:], d[2:]
        if s.startswith("f_") or d.startswith("f_"):
            continue          # frame ctl: none in the as-built census except rst/clock
        if s not in blk2part or d not in blk2part:
            continue
        ps, pd = blk2part[s], blk2part[d]
        if ps == pd:
            continue
        n_ctl += 1
        out.append(dict(id="ctl_%s_%s_%s" % (s, row["src_bus"], d), src=(ps, row["src_bus"] + "_o"),
                        dst=(pd, row["dst_bus"] + "_i"), width=int(row["bits"]), kind="ctl", cls="ctl"))
    ids = collections.Counter()
    for l in out:
        ids[l["id"]] += 1
        if ids[l["id"]] > 1:
            l["id"] = "%s_%d" % (l["id"], ids[l["id"]])
    return out, fmap, chains_meta


# ------------------------------------------------------------------------------------------------- routing
def route_all(parts, adj, links):
    P = {p.name: p for p in parts}
    load = collections.Counter()

    def cap(a, b):
        f, lo, hi = adj[a][b]
        return PINS_PER_UM * max(hi - lo - 10.0, 1.0)

    def cost(a, b, lk):
        pa, pb = P[a], P[b]
        (xa, ya), (xb, yb) = pa.c(), pb.c()
        c = abs(xa - xb) + abs(ya - yb) + 400.0       # per-hop station penalty
        u = (load[tuple(sorted((a, b)))] + lk["width"]) / cap(a, b)
        if u > 0.5:
            c += 20000.0 * (u - 0.5) ** 2 + (1e6 if u > 1.0 else 0.0)
        if pb.kind in HARD_KINDS:
            c += 1e9
        if pb.kind == "frame" and b != lk["dst"][0] and b not in lk.get("allow", ()):
            c += 1e8
        return c

    paths = {}
    for lk in sorted(links, key=lambda l: -l["width"]):
        s, d = lk["src"][0], lk["dst"][0]
        if s == d:
            paths[lk["id"]] = [s]
            continue
        if d in adj[s] and load[tuple(sorted((s, d)))] + lk["width"] <= 0.6 * cap(s, d):
            paths[lk["id"]] = [s, d]
            load[tuple(sorted((s, d)))] += lk["width"]
            continue
        # Dijkstra over (partition, entry face) so a lane never leaves through the face it came in on
        start = (s, None)
        dist = {start: 0.0}
        prev = {}
        pq = [(0.0, s, None)]
        goal = None
        while pq:
            c0, u, fin = heapq.heappop(pq)
            if u == d:
                goal = (u, fin)
                break
            if c0 > dist[(u, fin)]:
                continue
            for v in adj[u]:
                if v != d and P[v].kind in HARD_KINDS:
                    continue
                fout = adj[u][v][0]
                if fin is not None and fout == fin:
                    continue
                st = (v, adj[v][u][0])
                c1 = c0 + cost(u, v, lk)
                if c1 < dist.get(st, 1e30):
                    dist[st] = c1
                    prev[st] = (u, fin)
                    heapq.heappush(pq, (c1, v, st[1]))
        if goal is None:
            paths[lk["id"]] = None
            continue
        path = [goal]
        while path[-1] != start:
            path.append(prev[path[-1]])
        paths[lk["id"]] = [x[0] for x in path[::-1]]
        for x, y in zip(paths[lk["id"]], paths[lk["id"]][1:]):
            load[tuple(sorted((x, y)))] += lk["width"]
    return paths


# ---------------------------------------------------------------------------------------------- plan build
def build_plan(parts, adj, links, paths, chans, geo):
    P = {p.name: p for p in parts}
    face_load = collections.defaultdict(list)      # (a,b) unordered -> list of (port id, width)
    ports, lanes, unrouted = [], [], []
    slot_ct = collections.Counter()
    hops_bad = []
    lane_stats = {}
    for lk in links:
        path = paths.get(lk["id"])
        if not path or len(path) < 2:
            unrouted.append(lk["id"])
            continue
        pids = []
        stations_total = 0
        for i, (a, b) in enumerate(zip(path, path[1:])):
            pid = "%s__%d" % (lk["id"], i)
            pids.append(pid)
            src_bus = lk["src"][1] if i == 0 else None
            dst_bus = lk["dst"][1] if i == len(path) - 2 else None
            face_load[tuple(sorted((a, b)))].append((pid, lk["width"]))
            ports.append(dict(id=pid, a=a, b=b, src_bus=src_bus, dst_bus=dst_bus, width=lk["width"],
                              kind=lk["kind"], lane=lk["id"]))
        # ft slots in intermediate partitions
        for j in range(1, len(path) - 1):
            p = P[path[j]]
            fin = adj[p.name][path[j - 1]][0]
            fout = adj[p.name][path[j + 1]][0]
            ext = (p.w if fin in "EW" else p.h) if fin == dict(N="S", S="N", E="W", W="E")[fout] else \
                (p.w + p.h) / 2.0
            st = max(1, math.ceil(ext / REACH * 1.0 - 1e-9))
            # hop check: stations evenly spaced; worst hop ~ ext/(st+1) + neighbour half; keep ext/st <= REACH
            while ext / (st + 0.0) > REACH:
                st += 1
            slot_ct[p.name] += 1
            p.slots.append(dict(lane=lk["id"], in_face=fin, out_face=fout, width=lk["width"], stations=st,
                                ext=ext))
            stations_total += st
        lanes.append(dict(id=lk["id"], ports=pids, cls=lk["cls"], stations=stations_total,
                          cycles=stations_total + 1))
        P[path[0]].buses.append(dict(name=lk["src"][1], dir="out", width=lk["width"], kind=lk["kind"], cls=lk["cls"],
                                     face=adj[path[0]][path[1]][0]))
        P[path[-1]].buses.append(dict(name=lk["dst"][1], dir="in", width=lk["width"], kind=lk["kind"], cls=lk["cls"],
                                      face=adj[path[-1]][path[-2]][0]))
    # window allocation per shared face
    faces = {}
    for key, lst in face_load.items():
        a, b = key
        f, lo, hi = adj[a][b]
        total = sum(w for _, w in lst)
        avail = (hi - lo) - 2 * 5.0
        faces[key] = dict(a=a, b=b, face=f, lo=lo, hi=hi, bits=total, ratio=total / (PINS_PER_UM * max(avail, 1)))
        pos = lo + 5.0
        scale = 1.0 if total <= PINS_PER_UM * avail else (PINS_PER_UM * avail) / total
        for pid, w in lst:
            L = w / PINS_PER_UM * scale
            faces.setdefault("_win", {})[pid] = (pos, pos + L)
            pos += L
    return ports, lanes, faces, unrouted, slot_ct


FLIP = {"R0": {}, "MY": dict(E="W", W="E"), "MX": dict(N="S", S="N"), "R180": dict(E="W", W="E", N="S", S="N")}


def tf(p, f):
    return FLIP[p.orient].get(f, f)


def type_key(p):
    sl = tuple(sorted((tf(p, s["in_face"]), tf(p, s["out_face"]), s["width"], s["stations"]) for s in p.slots))
    bu = tuple(sorted((b["dir"], b["width"], tf(p, b["face"]), b.get("cls", "")) for b in p.buses))
    return (p.base, sl, bu)


def cut_sweep(parts, ports_xy, step=250.0):
    """bits crossing every vertical / horizontal die line (port-to-port L segments) vs M4+M6 / M5+M7 tracks."""
    trk_h = 1 / 0.048 + 1 / 0.064     # M4 + M6 per um of a vertical cut (H wires cross it)
    trk_v = 1 / 0.048 + 1 / 0.064     # M5 + M7
    res = {"V": [], "H": []}
    for x in [i * step for i in range(1, int(DIE[0] / step))]:
        bits = sum(w for (x0, y0, x1, y1, w) in ports_xy if min(x0, x1) < x < max(x0, x1))
        res["V"].append((x, bits, bits / (trk_h * DIE[1])))
    for y in [i * step for i in range(1, int(DIE[1] / step))]:
        bits = sum(w for (x0, y0, x1, y1, w) in ports_xy if min(y0, y1) < y < max(y0, y1))
        res["H"].append((y, bits, bits / (trk_v * DIE[0])))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asbuilt", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--y-arr", type=float, default=None)
    a = ap.parse_args()
    ab = json.load(open(a.asbuilt))
    census = list(csv.DictReader(open(a.census), delimiter="\t"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    groups = frame_mapping(ab)
    rplan = row_plan()
    best = None
    # choose array y and per-row flips (b0 = exit band) to minimise vertical lane travel to the slice bands
    for yi in range(0, 260):
        y_arr = snap(X0 + 120 * G + yi * G)
        if y_arr + NROW * FH + 4 * SER_H > YTOP + 1e-6:
            break
        geo_y = dict(yL0=X0 + 2 * IRG_H + 2 * SVC_H)
        yL0 = geo_y["yL0"]
        yU0 = yL0 + SL_H
        tot = 0.0
        fl = {}
        for side in ("W", "E"):
            fl[side] = []
            for r, (band, halves) in enumerate(rplan[side]):
                lo, hi = (yL0, yU0) if band == "L" else (yU0, yU0 + SL_H)
                best_r = None
                for flip in ((False, True) if MIRROR else (False,)):
                    y = y_arr + r * FH + (2 * BH if flip else 0)
                    c = max(0.0, lo - (y + BH)) + max(0.0, y - hi)
                    if best_r is None or c < best_r[0]:
                        best_r = (c, flip)
                tot += best_r[0]
                fl[side].append(best_r[1])
        if best is None or tot < best[0]:
            best = (tot, y_arr, fl)
    _, y_arr, flips = best
    if a.y_arr is not None:
        y_arr = a.y_arr
    parts, fslots, chans, geo = build_floorplan(ab, y_arr, flips)
    adj = adjacency(parts)
    links, fmap, chains_meta = logical_links(ab, census, fslots, groups, rplan)
    # frame band contents: the as-built frame mapped to this slot (h9 or h10), region r<b> of its landed kit
    master = {b["name"]: b["master"] for b in ab["blocks"]}
    for f, key in fmap.items():
        m = "col_h10" if master[f] == "col_h10" else "col_h9"
        for b, p in enumerate(fslots[key]):
            p.base = "fband_%s_r%d" % (m[4:], b)
            p.contents = [dict(inst="u_%s_r%d" % (f, b), module="%s_l4_lp.r%d" % (m, b), kind="frame",
                               note="region r%d of the landed frame %s (as-built %s)" % (b, m, f))]
    paths = route_all(parts, adj, links)
    ports, lanes, faces, unrouted, slot_ct = build_plan(parts, adj, links, paths, chans, geo)
    P = {p.name: p for p in parts}
    # types
    tkeys = {}
    for p in parts:
        tkeys.setdefault(type_key(p), []).append(p.name)
    # port geometry for the cut sweep and render
    win = faces.get("_win", {})
    pxy = []
    for pt in ports:
        pa, pb = P[pt["a"]], P[pt["b"]]
        pxy.append((pa.c()[0], pa.c()[1], pb.c()[0], pb.c()[1], pt["width"]))
    cuts = cut_sweep(parts, pxy)
    face_list = [v for k, v in faces.items() if k != "_win"]
    worst_faces = sorted(face_list, key=lambda f: -f["ratio"])[:15]
    stats = dict(
        y_arr=y_arr, flips=flips, partitions=len(parts),
        partitions_by_kind=collections.Counter(p.kind for p in parts),
        types=len(tkeys),
        types_by_kind=collections.Counter(P[v[0]].kind for v in tkeys.values()),
        links=len(links), unrouted=unrouted[:20], n_unrouted=len(unrouted),
        ports=len(ports), lanes=len(lanes),
        worst_faces=[dict(a=f["a"], b=f["b"], face=f["face"], bits=f["bits"], len=round(f["hi"] - f["lo"], 1),
                          ratio=round(f["ratio"], 3)) for f in worst_faces],
        faces_over_1=sum(1 for f in face_list if f["ratio"] > 1.0),
        faces_over_06=sum(1 for f in face_list if f["ratio"] > 0.6),
        worst_cut_V=max(cuts["V"], key=lambda t: t[2]), worst_cut_H=max(cuts["H"], key=lambda t: t[2]),
        stations_total=sum(l["stations"] for l in lanes),
        lane_cycles_max=max(l["cycles"] for l in lanes),
        ft_slots_total=sum(len(p.slots) for p in parts),
        ft_slots_by_kind=collections.Counter(p.kind for p in parts for _ in p.slots),
        channels=len(chans),
    )
    json.dump(dict(stats=stats, types={str(i): v for i, v in enumerate(tkeys.values())}), open(out / "stats.json", "w"),
              indent=1, default=str)
    json.dump(dict(parts=[dict(name=p.name, base=p.base, kind=p.kind, x0=p.x0, y0=p.y0, w=p.w, h=p.h,
                               orient=p.orient, slots=p.slots, buses=p.buses, contents=p.contents, note=p.note)
                          for p in parts],
                   ports=ports, lanes=lanes, chans=chans, geo=geo, fmap=fmap, chains=chains_meta,
                   faces=[dict(f, **{}) for f in face_list], paths=paths),
              open(out / "plan_internal.json", "w"), indent=0, default=str)
    print(json.dumps(stats, indent=1, default=str))


if __name__ == "__main__":
    main()
