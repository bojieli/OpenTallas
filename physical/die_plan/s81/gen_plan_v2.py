#!/usr/bin/env python3
"""PLAN-S81v2: S81 (DeepSeek ROM, 72-frame MU release) die plan v2 on a die lattice (TOPDOWN-PLAN, owner 10-23).

v2 vs v1 (COORD 04:46 + GEOM-REVIEW2 G1 04:47 on @0a79ca1ae):
  * ONE lattice for the whole die: cell = frame band 1442.88 x 1226.88 (167 x 142 grid of 8.64).  22 x 20 cells.
    Every partition is one cell (or a few cells for the hard HBM PHY and the units/serdes that need them).
  * Centre = a regular grid: slices are N-S chains of 1-cell segments (lep halves 2 x 8 / 2 x 7), svc 2 x 8 cells,
    cte row (ctrl pair + etap pair per svc column), irg columns, HBM PHY at the S edge, units + serdes at the N edge.
  * No lane columns: arrays abut the slices; W<->centre lanes run straight E-W through slice segments and frame b0
    bands as feedthrough (ft slots), Manhattan with <= 2 bends (router enumerates I/L/Z routes only).
  * Mirror symmetry: E array / E centre half are MY copies of the W ones; frames are MX (r0 band on top) / R180.
    PLAN-TOOL @764076fe6 symmetric tracks make mirrored copies ONE type; pins are declared on the TYPE.
  * No tie-offs: frame lk -> type parameter LK (per chain position), slice sid -> counted ID ring (seqhost -> slices
    -> seqhost, carries the fault OR), svc sid -> counted ID ring (seqhost -> rsv), slice ch_b -> parameter, slice bi
    -> BI_EN parameter (port only where a real PV source exists), rt padding -> N_RT parameter (one 70-b rt bus per
    frame), unit straps -> type parameters, frame chain-end xo -> XO_EN 0.
Inputs (read-only): cap30 gen-main plan.json (blocks + data links), FT census lanes tsv (ctl groups).
Output: OUT/die_plan.json + OUT/v2_stats.json + OUT/instance_map.json.
"""
import argparse
import collections
import csv
import json
import math
import re
from pathlib import Path

G = 8.64
PX, PY = 167 * G, 142 * G          # 1442.88 x 1226.88 cell (= frame band)
X0 = 12 * G                        # 103.68 seal ring
NC, NR = 22, 20
DIE_W = NC * PX + 2 * X0
DIE_H = NR * PY + 2 * X0
REACH = 1500.0
UNIFORM_SEG = True
SNAP = 0.192
TR = dict(M4=(0.048, 0.024), M5=(0.048, 0.024), M6=(0.064, 0.032), M7=(0.064, 0.032))   # pitch, offset
ALLOC_PPU = 4.6                    # pins/um inside a window (G0 limit 6/um in any 10-um window)
FACE_MAX = 0.6 * 6.0               # pins/um averaged over a cell face (COORD: face <= 0.6)
EDGE = 6.0
GAP = 2.0
XW, RW = 1104, 70
OPP = dict(N="S", S="N", E="W", W="E")
STEP = dict(E=(1, 0), W=(-1, 0), N=(0, 1), S=(0, -1))
FRAME_INTERNAL = [("r0", "r1", 1263), ("r1", "r2", 1229), ("r2", "r1", 384), ("r1", "r0", 141)]


def mir(c):
    return NC - 1 - c


# ------------------------------------------------------------------------------------------------ partitions
class Part:
    def __init__(self, name, kind, c0, r0, nc=1, nr=1, orient="R0", contents=None, hard=False, ckey=None,
                 note="", group=None, ft_ok=True):
        self.name, self.kind, self.c0, self.r0, self.nc, self.nr = name, kind, c0, r0, nc, nr
        self.orient, self.contents, self.hard, self.note = orient, contents or [], hard, note
        self.ckey = ckey or name          # content key (type identity of the contents)
        self.group = group                # e.g. slice half name
        self.ft_ok = ft_ok and not hard
        self.ents = []                    # interface entries

    @property
    def x0(self):
        return X0 + self.c0 * PX

    @property
    def y0(self):
        return X0 + self.r0 * PY

    @property
    def w(self):
        return self.nc * PX

    @property
    def h(self):
        return self.nr * PY

    def cells(self):
        return [(c, r) for c in range(self.c0, self.c0 + self.nc) for r in range(self.r0, self.r0 + self.nr)]

    @property
    def xflip(self):
        return self.orient in ("MY", "R180")

    @property
    def yflip(self):
        return self.orient in ("MX", "R180")


def C(inst, module, status="rework", params=None, note=None):
    d = dict(inst=inst, module=module, status=status)
    if params:
        d["params"] = params
    if note:
        d["note"] = note
    return d


def build(ab):
    blk = {b["name"]: b for b in ab["blocks"]}
    parts = []

    def add(p):
        parts.append(p)
        return p

    # ---- frame arrays: rows 1..18, frame rows fr = 0..5 at rows 1+3fr .. 3+3fr, all MX (r0 band on top) ----
    # chain positions from the centre outward: p1 p2 p3 (inner chain) p4 p5 p6 (outer chain)
    frames = {}
    for side in "WE":
        for fr in range(6):
            for pos in range(1, 7):
                cw = 6 - pos                        # W column: p1 = col 5 ... p6 = col 0
                col = cw if side == "W" else mir(cw)
                orient = "MX" if side == "W" else "R180"
                for b in range(3):
                    row = 3 + 3 * fr - b            # MX: r0 top band, r1 middle, r2 bottom
                    p = add(Part("f%s%d_p%d_b%d" % (side, fr, pos, b), "frame", col, row, orient=orient))
                    frames[(side, fr, pos, b)] = p
    # ---- serdes (PHY model, re-aspected to a 2-cell row slot, soft: a strip beside the PHY carries ft) ----
    serdes = {}
    sd = {"WS0": ("W", 0, 4), "WS1": ("W", 0, 2), "WN0": ("W", 19, 4), "WN1": ("W", 19, 2), "WN2": ("W", 19, 0),
          "WN3": ("C", 19, 6), "ES0": ("E", 0, 4), "ES1": ("E", 0, 2), "EN0": ("E", 19, 4), "EN1": ("E", 19, 2)}
    for nm, (side, row, cw) in sd.items():
        col = cw if side != "E" else mir(cw) - 1
        orient = "MY" if side == "E" else "R0"
        serdes[nm] = add(Part("lk_" + nm, "serdes", col, row, nc=2, orient=orient,
                              contents=[C("u_phy", "ot_pdie_serdes", "rework",
                                          note="SerDes PHY model re-aspected into a 2885.76 x 1226.88 slot; a strip "
                                               "beside it holds the boundary flops and ft stations")],
                              ckey="serdes"))
    # ---- centre: cols 6..15 ----
    # row 0: s_0S | iqf | phy (8-13) | eng | s_7S ; seqhost at (10,5) beside the svc band
    add(Part("phy_hbm", "phy", 8, 0, nc=6, hard=True,
             contents=[C("u_phy_hbm", "ot_hbm3e_phy_v41x_aw30_e8p5", "reuse",
                         note="hard HBM3E PHY 8500 x 1177 in a 6-cell S-edge slot (bump field at the die edge)")],
             ckey="phy"))
    add(Part("iqf", "unit", 7, 0, contents=[C("u_iqf", "dsdv_idx_qf")], ckey="iqf"))
    add(Part("seqhost", "unit", 10, 5, contents=[C("u_seqhost", "dsdv_seq_host_mux", "rework",
                                                  params={"TAP_K": "8'h00", "SINK_K": "8'h00", "SELECT_HBE": "1'b0"})],
             ckey="seqhost", note="GEOM-REVIEW2: seqhost beside the svc band; its slice/svc fan-out = ID rings"))
    # svc 2 x 8 -> 8 columns svc_k (col 7+k, rows 1-4) of FOUR 1-cell partitions svc_k_q0..q3 (L1 + COORD 05:44 (1)).
    # The attn ladder (rails 2k<->2k+2, 2k+1<->2k+3: up to 14.2 kb across a column boundary; fold rung up to 7.8 kb)
    # does not fit one 1.44-mm face, so the svc attn datapath of the fold pair (rsv_2k + rsv_2k+1) is BIT-SLICED x4:
    # cell q holds bits [q*W/4, (q+1)*W/4) of both rsv of the pair -> the rung stays inside each cell and every rail
    # crosses four cell faces (one quarter each, same latency).  q0 (next to the PHY row) also holds ctrl_2k/2k+1,
    # etap_2k/2k+1 and irg_k (HBM side); a column spine (q <-> q+1) carries the control/sequencing broadcast.
    svcg = {}
    for k in range(8):
        ma, mb = blk["rsv_%02d" % (2 * k)]["master"], blk["rsv_%02d" % (2 * k + 1)]["master"]
        segs = {}
        for q in range(4):
            cont = [C("u_rsv_a", "%s.bs%d" % (ma, q), "rework",
                      note="svc 2k attn datapath bit slice %d/4 (+ its share of the svc control)" % q),
                    C("u_rsv_b", "%s.bs%d" % (mb, q), "rework",
                      note="svc 2k+1 bit slice %d/4; the fold rung of this slice is internal" % q)]
            if q == 0:
                cont += [C("u_ctrl_a", "dsfd_ctrl_rg3_native32", "reuse"),
                         C("u_ctrl_b", "dsfd_ctrl_rg3_native32", "reuse"),
                         C("u_etap_a", "dsdv_eng_tap_w" if k == 0 else "dsdv_eng_tap", "reuse"),
                         C("u_etap_b", "dsdv_eng_tap", "reuse"),
                         C("u_irg", "dsdv_idx_rg3", "reuse",
                           note="irg_k serves etap_2k/2k+1: merged into svc_k_q0 (its etap links are internal)")]
            segs[(0, q)] = add(Part("svc_%d_q%d" % (k, q), "svc", 7 + k, 1 + q, orient="R0" if k < 4 else "MY",
                                    contents=cont, ckey="svc_q%d_%s_%s%s" % (q, ma, mb, "_w" if (k == 0 and q == 0)
                                                                              else ""), group="svc_%d" % k))
        svcg["svc_%d" % k] = dict(segs=segs)
    # slices: S halves rows 5..11 (7), N halves rows 12..18 (7); columns s_0 6-7, s_1..s_6 8..13, s_7 14-15
    slices = {}
    colmap = {0: (6, 2), 1: (8, 1), 2: (9, 1), 3: (10, 1), 4: (11, 1), 5: (12, 1), 6: (13, 1), 7: (14, 2)}
    for k in range(8):
        c0, ncol = colmap[k]
        for half, (r0, nrow) in (("S", (5, 7)), ("N", (12, 7))):
            hn = "s_%d%s" % (k, half)
            if hn == "s_3S":
                r0, nrow = 6, 6          # (10,5) = seqhost, beside the svc band
            if hn in ("s_0S", "s_7S"):
                r0, nrow = 0, 12         # lep S halves also take the outer column down to the PHY row (rows 0-4)
            if hn == "s_7N":
                nrow = 8                 # lep E N half reaches the top row (W twin's top cell row = WN3)
            m = blk[hn]["master"]
            segs = {}
            for dc in range(ncol):
                for dr in range(nrow):
                    if r0 + dr < 5 and (c0 + dc) in range(7, 15):
                        continue                 # svc band cell
                    # segment index in the half's own frame: W half counts columns from the W side, E half (MY) mirrored
                    sc = dc if k < 4 else (ncol - 1 - dc)
                    nm = "%s_g%d%d" % (hn, sc, dr)
                    p = add(Part(nm, "slice", c0 + dc, r0 + dr, orient="R0" if k < 4 else "MY",
                                 contents=[C("u_seg", ("%s.seg" % m) if UNIFORM_SEG else "%s.seg%d%d" % (m, sc, dr), "rework",
                                             note="segment (%d,%d) of the slice half re-derived as an N-S chain of "
                                                  "1-cell partitions (regions assigned by the slice re-derivation)"
                                                  % (sc, dr))],
                                 ckey=("%s.seg" % m) if UNIFORM_SEG else ("%s.seg%d%d" % (m, sc, dr)), group=hn))
                    segs[(dc, dr)] = p
            slices[hn] = dict(master=m, c0=c0, r0=r0, ncol=ncol, nrow=nrow, segs=segs, k=k, half=half)
    # units row 19: WN3 (6-7) | bk_col 8 | gunit 9-10 | bk_sel 11-13 | s_7N top (14-15)
    add(Part("bk_col", "unit", 8, 19, contents=[C("u_bk_col", "dsfd_bk_collector")], ckey="bk_col"))
    add(Part("gunit", "unit", 9, 19, nc=2, contents=[C("u_gunit", "dsdv_gunit", "rework", params={"SID": "4'd3"},
                                                       note="re-aspected 950x1469 -> 2-cell row slot")],
             ckey="gunit"))
    add(Part("bk_sel", "unit", 11, 19, nc=3, contents=[C("u_bk_sel", "dsdv_bk_sel_vmtx", "rework",
                                                        params={"TAP_K": "8'h11", "SINK_K": "8'h10", "IK": "3'd4",
                                                                "EK": "3'd5", "UID": "8'h5B", "EG_N": "1'b0"},
                                                        note="re-aspected 907x4536 -> 3-cell row slot")],
             ckey="bk_sel"))
    add(Part("eng", "unit", 14, 0, contents=[C("u_eng", "dsdv_eng_rr")], ckey="eng"))
    chans = [dict(rect_um=[X0 + c * PX, X0 + r * PY, X0 + (c + 2) * PX, X0 + (r + 1) * PY],
                  reason="die-corner end of the SerDes PHY row: bump/ESD keep-out of the corner PHY (no logic routes "
                         "here; both neighbours are PHY or seal ring)")
             for c, r in ((0, 0), (20, 0), (20, 19))]
    return parts, frames, serdes, slices, chans, svcg


# ---------------------------------------------------------------------------------------------- logical lanes
def frame_mapping(ab):
    blk = {b["name"]: b for b in ab["blocks"]}
    srv = collections.defaultdict(list)
    for l in ab["links"]:
        if l["c"] == "ret":
            srv[ab["blocks"][l["e"][1][0]]["name"]].append(ab["blocks"][l["e"][0][0]]["name"])
    groups = {}
    for s, fr in srv.items():
        fr = sorted(fr)
        chains = [fr[i:i + 3] for i in range(0, len(fr), 3)]       # [01,02,03] / [10,12,13] per chain
        groups[s] = [[(f, blk[f]["master"]) for f in ch] for ch in chains]
    return groups


# side -> frame row -> (inner half, outer half); S rows fr 0..2, N rows 3..5; x rows = 3 + 3 fr
ROWPLAN = {"W": {0: ("s_0S", "s_0S"), 1: ("s_2S", "s_2S"), 2: ("s_1S", "s_3S"),
                 3: ("s_1N", "s_3N"), 4: ("s_2N", "s_2N"), 5: ("s_0N", "s_0N")},
           "E": {0: ("s_7S", "s_7S"), 1: ("s_5S", "s_5S"), 2: ("s_6S", "s_4S"),
                 3: ("s_6N", "s_4N"), 4: ("s_5N", "s_5N"), 5: ("s_7N", "s_7N")}}
LK_ROLE = {1: "LK_HEAD", 2: "LK_MID", 3: "LK_TAIL", 4: "LK_HEAD", 5: "LK_MID", 6: "LK_TAIL"}


def x_row(fr):
    return 3 + 3 * fr


def lanes_all(ab, census, parts, frames, serdes, slices):
    P = {p.name: p for p in parts}
    groups = frame_mapping(ab)
    lanes = []
    fmap = {}

    def L(lid, src, sbus, dst, dbus, width, kind="data", cls="data", role=None, path=None):
        lanes.append(dict(id=lid, src=(src, sbus), dst=(dst, dbus), width=int(width), kind=kind, cls=cls,
                          role=role or cls, path=path))

    def cell_of(seg):
        return (seg.c0, seg.r0)

    # ---- frames: contents + internal + chain + x/ret lanes ----
    for side in "WE":
        used = collections.Counter()
        for fr in range(6):
            inner, outer = ROWPLAN[side][fr]
            ch_in = groups[inner][used[inner]]
            used[inner] += 1
            ch_out = groups[outer][used[outer]]
            used[outer] += 1
            for pos in range(1, 7):
                f, m = (ch_in if pos <= 3 else ch_out)[(pos - 1) % 3]
                h = "h10" if m == "col_h10" else "h9"
                fmap["f%s%d_p%d" % (side, fr, pos)] = f
                for b in range(3):
                    p = frames[(side, fr, pos, b)]
                    prm = {}
                    if b == 0:
                        prm = {"LK": LK_ROLE[pos], "XO_EN": 0 if pos in (3, 6) else 1}
                    p.contents = [C("u_r%d" % b, "col_%s_l4_lp.r%d" % (h, b), "rework", params=prm or None,
                                    note="region r%d of the landed frame col_%s (ROM image per instance)" % (b, h))]
                    p.ckey = "col_%s.r%d" % (h, b) + ((".p%d" % pos) if b == 0 else "")
                    p.group = f
                fb = [frames[(side, fr, pos, b)].name for b in range(3)]
                for a, bb, w in FRAME_INTERNAL:
                    ia, ib = int(a[1]), int(bb[1])
                    L("fi_%s%d_p%d_%s%s" % (side, fr, pos, a, bb), fb[ia], "%s%s_o" % (a, bb), fb[ib], "%s%s_i" % (a, bb),
                      w, cls="frame_int", role="fi_%s%s" % (a, bb))
            b0 = {pos: frames[(side, fr, pos, 0)].name for pos in range(1, 7)}
            xr = x_row(fr)
            for chain, (half, base) in (("in", (inner, 1)), ("out", (outer, 4))):
                sl = slices[half]
                # emitting segment: the half's segment on the x row, at the column nearest the array; fr0 S rows sit
                # one row below the S halves -> the bottom segment, path turns S then W/E
                dcol = 0 if side == "W" else sl["ncol"] - 1
                rr = xr if sl["r0"] <= xr < sl["r0"] + sl["nrow"] else sl["r0"]
                seg = sl["segs"][(dcol, rr - sl["r0"])]
                tag = "%s%d_%s" % (side, fr, chain)
                L("x_" + tag, seg.name, "xc_%s" % chain, b0[base], "x_i", XW, cls="x",
                  role="x_" + chain, path=("xrow", side, xr))
                L("xo_%s_a" % tag, b0[base], "xo_o", b0[base + 1], "x_i", XW, cls="xo", role="xo")
                L("xo_%s_b" % tag, b0[base + 1], "xo_o", b0[base + 2], "x_i", XW, cls="xo", role="xo")
                for k in range(3):
                    L("rt_%s_%d" % (tag, k), b0[base + k], "ret_o", seg.name, "rt_%s%d" % (chain, k), RW, cls="ret",
                      role="ret_p%d" % (base + k), path=("xrow", side, xr))
    # ---- slice spine (budget: x broadcast down + result up, 1104 b each way between vertical neighbours; lep
    #      halves also 1104 b each way between their two columns on every row) ----
    for hn, sl in slices.items():
        segs = sl["segs"]
        for (dc, dr), p in segs.items():
            if (dc, dr + 1) in segs:
                q = segs[(dc, dr + 1)]
                L("sp_%s_%d%d_u" % (hn, dc, dr), p.name, "spu_o", q.name, "spu_i", XW, cls="spine", role="spine_up")
                L("sp_%s_%d%d_d" % (hn, dc, dr), q.name, "spd_o", p.name, "spd_i", XW, cls="spine", role="spine_dn")
            if (dc + 1, dr) in segs and (sl["r0"] + dr) % 3 != 0:
                # lep cross-column spine on non-x rows only: the x-row cells carry the array x/rt feedthrough of the
                # inner slices and get their slice traffic over the vertical spine
                q = segs[(dc + 1, dr)]
                L("sp_%s_%d%d_e" % (hn, dc, dr), p.name, "spe_o", q.name, "spe_i", XW, cls="spine", role="spine_x")
                L("sp_%s_%d%d_w" % (hn, dc, dr), q.name, "spw_o", p.name, "spw_i", XW, cls="spine", role="spine_x")
    # ---- as-built non-frame links (aggregated per src part / dst part / class) ----
    def bpart(nm):
        if nm.startswith("ctrl_") or nm.startswith("etap_"):
            return "svc_%d" % (int(nm[5:]) // 2)
        if nm.startswith("irg_"):
            return "svc_%d" % int(nm[4:])
        if nm.startswith("rsv_"):
            return "svc_%d" % (int(nm[4:]) // 2)
        if nm.startswith("lk_"):
            return nm
        return nm

    agg = collections.OrderedDict()
    for l in ab["links"]:
        if l["c"] in ("x_frame", "ret"):
            continue
        src = ab["blocks"][l["e"][0][0]]["name"]
        for e in l["e"][1:]:
            dst = ab["blocks"][e[0]]["name"]
            ps, pd = bpart(src), bpart(dst)
            if ps == pd:
                continue
            key = (ps, pd, l["c"])
            agg.setdefault(key, [0, src, dst])
            agg[key][0] += int(l["b"])
    nctl = collections.Counter()
    for row in census:
        if row["kind"] != "ctl":
            continue
        s, d = row["src"], row["dst"]
        if not (s.startswith("u_") and d.startswith("u_")):
            continue
        s, d = s[2:], d[2:]
        if s.startswith("f_") or d.startswith("f_"):
            continue
        ps, pd = bpart(s), bpart(d)
        if ps == pd or ps not in P and ps not in slices or pd not in P and pd not in slices:
            continue
        nctl[(ps, pd)] += int(row["bits"])
    have = {(a, b) for (a, b, c) in agg}
    for (ps, pd), b in nctl.items():
        if (ps, pd) in have:
            continue      # control sub-fields of a plan.json bus (e.g. rd = r_data/r_tag/r_beat/rv/rk/wd/hs)
        agg[(ps, pd, "ctl")] = [b, ps, pd]
    for (ps, pd, c), (b, s0, d0) in agg.items():
        kind = "ctl" if c == "ctl" else "data"
        if c == "attn" and ps.startswith("svc_") and pd.startswith("svc_"):
            for q in range(4):      # bit-sliced attn rail: quarter q between the q cells
                wq = b // 4 + (1 if q < b % 4 else 0)
                L("%s__%s__%s__q%d" % (c, ps, pd, q), "%s_q%d" % (ps, q), "%s_%s_o" % (c, pd), "%s_q%d" % (pd, q),
                  "%s_%s_i" % (c, ps), wq, kind=kind, cls=c, role=c)
            continue
        L("%s__%s__%s" % (c, ps, pd), ps, "%s_%s_o" % (c, pd), pd, "%s_%s_i" % (c, ps), b, kind=kind, cls=c,
          role=c)
    # ---- svc column spine (control/sequencing broadcast between the bit slices; budget 276 b each way) ----
    for k in range(8):
        for q in range(3):
            a_, b_ = "svc_%d_q%d" % (k, q), "svc_%d_q%d" % (k, q + 1)
            L("sc_%d_%d_u" % (k, q), a_, "scu_o", b_, "scu_i", 276, cls="svccol", role="svccol_up")
            L("sc_%d_%d_d" % (k, q), b_, "scd_o", a_, "scd_i", 276, cls="svccol", role="svccol_dn")
    # ---- ID rings (no tie-offs): slice sid + fault OR, svc sid; counted (sid_o = sid_i + 1), rooted at seqhost ----
    order_s = ["s_%dS" % k for k in range(7, -1, -1)] + ["s_%dN" % k for k in range(8)]
    ring = ["seqhost"] + order_s + ["seqhost"]
    for a, b in zip(ring, ring[1:]):
        L("sid_%s__%s" % (a, b), a, "sid_o" if a != "seqhost" else "sidr_o", b, "sid_i" if b != "seqhost" else "sidr_i",
          5, kind="ctl", cls="sid", role="sid")
    svc_ring = ["seqhost"] + ["svc_%d" % k for k in range(8)] + ["seqhost"]
    for a, b in zip(svc_ring, svc_ring[1:]):
        L("vid_%s__%s" % (a, b), a, "vid_o" if a != "seqhost" else "vidr_o", b, "vid_i" if b != "seqhost" else "vidr_i",
          4, kind="ctl", cls="vid", role="vid")
    return lanes, fmap


# --------------------------------------------------------------------------------------------------- routing
class Grid:
    def __init__(self, parts):
        self.owner = {}
        self.P = {p.name: p for p in parts}
        for p in parts:
            for c in p.cells():
                assert c not in self.owner, (c, p.name, self.owner.get(c))
                self.owner[c] = p.name
        self.load = collections.Counter()     # (cellA, cellB) sorted -> pins

    def cap(self, a, b):
        lo, hi, _ = span(self.P[self.owner[a]], self.P[self.owner[b]], a, b)
        return FACE_MAX * (hi - lo - 2 * EDGE)

    def fkey(self, a, b):
        # load is booked per shared partition boundary (a wide port may use the whole shared face)
        return bkey(self.owner[a], self.owner[b], a, b)


def bkey(na, nb, a, b):
    return tuple(sorted((na, nb))) + (a[1] == b[1],)


def span(pa, pb, a, b):
    """die-coordinate span (lo, hi) of the boundary shared by pa and pb that the cell step a->b crosses."""
    if a[1] == b[1]:     # side by side -> E/W face along y
        r0 = max(pa.r0, pb.r0)
        r1 = min(pa.r0 + pa.nr, pb.r0 + pb.nr)
        return X0 + r0 * PY, X0 + r1 * PY, True
    c0 = max(pa.c0, pb.c0)
    c1 = min(pa.c0 + pa.nc, pb.c0 + pb.nc)
    return X0 + c0 * PX, X0 + c1 * PX, False


def seg_path(a, b):
    """cells from a to b along a straight line (inclusive)."""
    (x0, y0), (x1, y1) = a, b
    out = []
    if x0 == x1:
        s = 1 if y1 >= y0 else -1
        out = [(x0, y) for y in range(y0, y1 + s, s)]
    else:
        s = 1 if x1 >= x0 else -1
        out = [(x, y0) for x in range(x0, x1 + s, s)]
    return out


def poly_cells(pts):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        out += seg_path(a, b)[1:]
    return out


def candidates(a, b):
    (ax, ay), (bx, by) = a, b
    if ax == bx or ay == by:
        yield [a, b]
        return
    yield [a, (bx, ay), b]
    yield [a, (ax, by), b]
    lo, hi = sorted((ax, bx))
    for m in range(lo + 1, hi):
        yield [a, (m, ay), (m, by), b]
    lo, hi = sorted((ay, by))
    for m in range(lo + 1, hi):
        yield [a, (ax, m), (bx, m), b]


XCOST = dict(svc=1.2, slice=0.6, unit=0.4, idx=0.4, serdes=0.6)


def route(grid, lanes, slices):
    P = grid.P
    res = {}
    order = sorted(lanes, key=lambda l: (l.get("path") is None, -l["width"]))
    for lk in order:
        s, d = lk["src"][0], lk["dst"][0]
        w = lk["width"] + 1
        if lk.get("path") and lk["path"][0] == "xrow":
            _, side, xr = lk["path"]
            # fixed: from the slice segment straight to the array on the x row (turn at the segment if the x row is
            # below the half), then through the frame b0 bands
            sp, dp = P[s], P[d]
            a_cell = (sp.c0, sp.r0)
            if lk["cls"] == "ret":
                a_cell = (dp.c0, dp.r0)
                fcell = (sp.c0, sp.r0)
            else:
                fcell = (dp.c0, dp.r0)
            pts = [a_cell, (a_cell[0], xr), fcell] if a_cell[1] != xr else [a_cell, fcell]
            cells = poly_cells(pts)
            if lk["cls"] == "ret":
                cells = cells[::-1]
            seq = cells
        else:
            both = s in slices and d in slices

            def cells_of(n):
                if n in slices:
                    cs = [c for q in slices[n]["segs"].values() for c in q.cells()]
                    # fixed slice rows per lane class (regular segment types): xring + ID ring on the ring row,
                    # xtier on the S top / N bottom rows
                    row = None
                    if both and lk["cls"] in ("xring", "sid"):
                        row = 7 if n.endswith("S") else 14
                    elif both and lk["cls"] == "xtier":
                        row = 11 if n.endswith("S") else 12
                    if row is not None and any(c[1] == row for c in cs):
                        cs = [c for c in cs if c[1] == row]
                    return cs
                return P[n].cells()
            best = None
            for ca in cells_of(s):
                for cb in cells_of(d):
                    for pts in candidates(ca, cb):
                        cells = poly_cells(pts)
                        cost = len(cells) * 1.0 + 0.3 * (len(pts) - 2)
                        ok = True
                        names = []
                        for c in cells:
                            o = grid.owner.get(c)
                            if o is None:
                                ok = False
                                break
                            if not names or names[-1] != o:
                                names.append(o)
                        if not ok or len(set(names)) != len(names):
                            continue
                        for o in names[1:-1]:
                            q = P[o]
                            if not q.ft_ok or q.kind == "frame" or (q.kind == "serdes" and not (s.startswith("lk_") or d.startswith("lk_"))):
                                ok = False
                                break
                            cost += XCOST.get(q.kind, 0.6)        # station / partition crossing (pin-limited kinds dearer)
                        if not ok:
                            continue
                        over = 0.0
                        for x, y in zip(cells, cells[1:]):
                            if grid.owner[x] == grid.owner[y]:
                                continue
                            k = grid.fkey(x, y)
                            u = (grid.load[k] + w) / grid.cap(x, y)
                            if u > 1.0:
                                over += 1e4
                            elif u > 0.7:
                                cost += 5 * (u - 0.7)
                        cost += over
                        if best is None or cost < best[0]:
                            best = (cost, cells, pts)
            if best is None:
                raise SystemExit("no route for %s" % lk["id"])
            seq = best[1]
            lk["src"] = (grid.owner[seq[0]], lk["src"][1])
            lk["dst"] = (grid.owner[seq[-1]], lk["dst"][1])
        # apply load
        for x, y in zip(seq, seq[1:]):
            if grid.owner[x] != grid.owner[y]:
                grid.load[grid.fkey(x, y)] += w
        res[lk["id"]] = seq
    return res


def bends(cells):
    dirs = []
    for a, b in zip(cells, cells[1:]):
        d = (b[0] - a[0], b[1] - a[1])
        if not dirs or dirs[-1] != d:
            dirs.append(d)
    return max(0, len(dirs) - 1)


# --------------------------------------------------------------------------------------------- plan emission
def face_dir(a, b):
    d = (b[0] - a[0], b[1] - a[1])
    return {(1, 0): "E", (-1, 0): "W", (0, 1): "N", (0, -1): "S"}[d]


TF = {"R0": {}, "MY": dict(E="W", W="E"), "MX": dict(N="S", S="N"), "R180": dict(E="W", W="E", N="S", S="N")}


def to_type_win(p, face, lo, hi):
    if face in "EW":
        a, b, flip, ext = lo - p.y0, hi - p.y0, p.yflip, p.h
    else:
        a, b, flip, ext = lo - p.x0, hi - p.x0, p.xflip, p.w
    if flip:
        a, b = ext - b, ext - a
    return round(a, 4), round(b, 4), flip


KPRIO = dict(frame=0, serdes=1, svc=2, cte=2, idx=2, slice=3, unit=4, phy=5)


def emit(parts, lanes, routes, chans, fmap, out):
    P = {p.name: p for p in parts}
    grid_owner = {}
    for p in parts:
        for c in p.cells():
            grid_owner[c] = p.name
    # ports per lane
    ports = []
    lane_ports = {}
    for lk in lanes:
        cells = routes[lk["id"]]
        pids = []
        i = 0
        for x, y in zip(cells, cells[1:]):
            a, b = grid_owner[x], grid_owner[y]
            if a == b:
                continue
            pid = "%s__%d" % (lk["id"], i)
            i += 1
            ports.append(dict(id=pid, a=a, b=b, ca=x, cb=y, face=face_dir(x, y), width=lk["width"], kind=lk["kind"],
                              lane=lk["id"], cls=lk["cls"], role=lk["role"]))
            pids.append(pid)
        lane_ports[lk["id"]] = pids
    PT = {pt["id"]: pt for pt in ports}
    # windows per cell face, allocated in the type frame of the higher-priority partition
    byface = collections.defaultdict(list)
    for pt in ports:
        byface[bkey(pt["a"], pt["b"], pt["ca"], pt["cb"])].append(pt)
    win = {}
    over = []
    for key, lst in byface.items():
        ca, cb = lst[0]["ca"], lst[0]["cb"]
        pa, pb = P[grid_owner[ca]], P[grid_owner[cb]]
        alloc = min((pa, pb), key=lambda q: (KPRIO[q.kind], q.name))
        lo, hi, vertical_face = span(pa, pb, ca, cb)
        L_ = hi - lo
        flip = alloc.yflip if vertical_face else alloc.xflip

        def skey(pt):
            # canonical, position-free order: role, width, flow direction seen from the allocating partition
            f = pt["face"] if pt["a"] == alloc.name else OPP[pt["face"]]
            outw = pt["a"] == alloc.name
            return (pt["role"], -pt["width"], outw, TF[alloc.orient].get(f, f), pt["lane"])
        lst.sort(key=skey)
        need = sum((pt["width"] + 1) / ALLOC_PPU + GAP for pt in lst)
        avail = L_ - 2 * EDGE
        scale = min(1.0, avail / need)
        ratio = sum(pt["width"] + 1 for pt in lst) / (6.0 * L_)
        over.append((ratio, grid_owner[ca], grid_owner[cb], key, sum(pt["width"] + 1 for pt in lst), L_))
        pos = (hi - EDGE) if flip else (lo + EDGE)
        for pt in lst:
            Lw = (pt["width"] + 1) / ALLOC_PPU * scale
            g = GAP * scale
            if flip:
                w0, w1, pos = pos - Lw, pos, pos - Lw - g
            else:
                w0, w1, pos = pos, pos + Lw, pos + Lw + g
            # snap to the 0.192-um grid (a multiple of every M4-M7 pitch; the lattice 8.64 = 45 x 0.192): window
            # edges then sit half a pitch from the nearest track in every instance frame -> identical pin tables
            q0, q1 = math.ceil(w0 / SNAP - 1e-6), math.floor(w1 / SNAP + 1e-6)
            lo_, hi_ = q0 * SNAP, q1 * SNAP
            # PLAN-TOOL pins sit symmetric about the window's centre track per layer; when k0 + k1 is odd for a
            # layer the span sits half a track low and a mirrored copy lands one pitch off -> trim hi until every
            # layer of the face has an even k0 + k1 (mirror-invariant pin table)
            lays_ = ["M6", "M4"] if vertical_face else ["M7", "M5"]
            # (trim the end that is the TYPE-frame high end of the allocating partition, so mirrored copies agree)
            for d in range(0, 200):
                l2, h2 = (lo_ + d * 0.004, hi_) if flip else (lo_, hi_ - d * 0.004)
                if all((math.ceil((l2 - TR[l][1]) / TR[l][0] - 1e-9) +
                        math.floor((h2 - TR[l][1]) / TR[l][0] + 1e-9)) % 2 == 0 for l in lays_):
                    lo_, hi_ = l2, h2
                    break
            else:
                raise SystemExit("no even-parity window for %s" % pt["id"])
            win[pt["id"]] = (round(lo_, 4), round(hi_, 4))
    # bit order: ONE die-frame order per lane (a ft slot has one order for both faces); it is lsb_low in the type
    # frame of the lane's anchor end (a frame end if any, else the source), so mirrored copies keep one type
    for lid, pids in lane_ports.items():
        if not pids:
            continue
        p0, p1 = PT[pids[0]], PT[pids[-1]]
        if P[p1["b"]].kind == "frame" and P[p0["a"]].kind != "frame":
            anc, face = P[p1["b"]], OPP[p1["face"]]
        else:
            anc, face = P[p0["a"]], p0["face"]
        fl = anc.yflip if face in "EW" else anc.xflip
        for pid in pids:
            PT[pid]["order"] = "lsb_high" if fl else "lsb_low"
    # interface entries per partition
    for pt in ports:
        w0, w1 = win[pt["id"]]
        for role, part, df in (("out", pt["a"], pt["face"]), ("in", pt["b"], OPP[pt["face"]])):
            p = P[part]
            a, b, flip = to_type_win(p, df, w0, w1)
            tface = TF[p.orient].get(df, df)
            # bit order in the type frame
            border = pt["order"]
            if flip:
                border = "lsb_high" if border == "lsb_low" else "lsb_low"
            p.ents.append(dict(dir=role, port=pt["id"], lane=pt["lane"], face=tface, win=(a, b), width=pt["width"],
                               kind=pt["kind"], cls=pt["cls"], role_=pt["role"], order=border))
    # pair ft crossings
    lane_idx = {}
    for lid, pids in lane_ports.items():
        for i, pid in enumerate(pids):
            lane_idx[pid] = (lid, i, len(pids))

    def port_pt(pid):
        pt = PT[pid]
        w0, w1 = win[pid]
        m = (w0 + w1) / 2
        x0 = X0 + pt["ca"][0] * PX
        y0 = X0 + pt["ca"][1] * PY
        f = pt["face"]
        return {"E": (x0 + PX, m), "W": (x0, m), "N": (m, y0 + PY), "S": (m, y0)}[f]

    sigs = {}
    for p in parts:
        ins = {e["port"]: e for e in p.ents if e["dir"] == "in"}
        outs = {e["port"]: e for e in p.ents if e["dir"] == "out"}
        slots, func, used = [], [], set()
        for pid, ei in ins.items():
            lid, i, n = lane_idx[pid]
            if i + 1 < n:
                nxt = lane_ports[lid][i + 1]
                if nxt in outs:
                    eo = outs[nxt]
                    a_, b_ = port_pt(pid), port_pt(nxt)
                    Ld = abs(a_[0] - b_[0]) + abs(a_[1] - b_[1])
                    st = max(1, math.ceil(Ld / (REACH * 0.98)))
                    slots.append((ei, eo, st))
                    used |= {pid, nxt}
        for e in p.ents:
            if e["port"] not in used:
                func.append(e)
        fsig = tuple(sorted((e["dir"], e["face"], e["win"], e["width"], e["kind"], e["cls"], e["order"]) for e in func))
        ssig = tuple(sorted((ei["face"], ei["win"], eo["face"], eo["win"], ei["width"], ei["kind"], ei["order"],
                             eo["order"], st) for ei, eo, st in slots))
        ckey = json.dumps(p.contents, sort_keys=True)
        key = (p.ckey, ckey, round(p.w, 3), round(p.h, 3), p.hard, fsig, ssig)
        sigs[p.name] = (key, func, slots)
    types = collections.OrderedDict()
    for p in parts:
        types.setdefault(sigs[p.name][0], []).append(p.name)
    tname = {}
    cnt = collections.Counter()
    for key in types:
        base = re.sub(r"[^A-Za-z0-9_]", "_", key[0])
        cnt[base] += 1
        tname[key] = "%s__t%d" % (base, cnt[base])
    out_types, busname, ptype = {}, {}, {}

    def fsort(e):
        return (e["dir"], e["face"], e["win"], e["width"], e["kind"], e["cls"], e["order"])

    def ssort(t):
        ei, eo, st = t
        return (ei["face"], ei["win"], eo["face"], eo["win"], ei["width"], ei["kind"], ei["order"], eo["order"], st)

    def lays(face):
        return ["M6", "M4"] if face in "EW" else ["M7", "M5"]

    for key, names in types.items():
        tn = tname[key]
        rep = P[names[0]]
        _, func, slots = sigs[names[0]]
        fs = sorted(func, key=fsort)
        buses, canon = [], []
        cc = collections.Counter()
        for e in fs:
            nm = "%s_%s%d" % (e["cls"], "o" if e["dir"] == "out" else "i", cc[(e["cls"], e["dir"])])
            cc[(e["cls"], e["dir"])] += 1
            canon.append(nm)
            buses.append(dict(name=nm, dir=e["dir"], width=e["width"], kind=e["kind"], face=e["face"],
                              window_um=list(e["win"]), layers=lays(e["face"]), order=e["order"]))
        ss = sorted(slots, key=ssort)
        ftsl = []
        for i, (ei, eo, st) in enumerate(ss):
            ftsl.append(dict(name="ft%d" % i, in_face=ei["face"], out_face=eo["face"], width=ei["width"],
                             stations=st, in_window_um=list(ei["win"]), out_window_um=list(eo["win"]),
                             layers=lays(ei["face"]) if ei["face"] in "EW" and eo["face"] in "EW" else
                             (lays(ei["face"]) if ei["face"] in "NS" and eo["face"] in "NS" else None),
                             order=ei["order"]))
        for s_ in ftsl:
            if s_["layers"] is None:
                s_.pop("layers")
        ty = dict(module="s81p_" + tn, outline_um=[rep.w, rep.h], hard=rep.hard, buses=buses, ft_slots=ftsl,
                  clock=dict(tap_um=[round(rep.w / 2 / G) * G, round(rep.h / 2 / G) * G], layer="M9"),
                  reset=dict(sync_stages=2), contents=rep.contents,
                  note="%s partition; %d instance(s) (%s)" % (rep.kind, len(names),
                                                              ",".join(sorted({P[n].orient for n in names}))))
        out_types[tn] = ty
        for n in names:
            _, f2, s2 = sigs[n]
            for e, nm in zip(sorted(f2, key=fsort), canon):
                busname[(n, e["port"], e["dir"])] = nm
            for i, (ei, eo, st) in enumerate(sorted(s2, key=ssort)):
                busname[(n, ei["port"], "in")] = "ft%d_i" % i
                busname[(n, eo["port"], "out")] = "ft%d_o" % i
            ptype[n] = tn
    oparts = [dict(name=p.name, type=ptype[p.name], origin_um=[round(p.x0, 4), round(p.y0, 4)], orient=p.orient)
              for p in parts]
    oports = []
    for pt in ports:
        w0, w1 = win[pt["id"]]
        oports.append(dict(id=pt["id"], src=dict(part=pt["a"], bus=busname[(pt["a"], pt["id"], "out")]),
                           dst=dict(part=pt["b"], bus=busname[(pt["b"], pt["id"], "in")]), width=pt["width"],
                           kind=pt["kind"], face=pt["face"], layers=lays(pt["face"]), window_um=[w0, w1],
                           order=pt["order"]))
    olanes = [dict(id=l["id"], ports=lane_ports[l["id"]]) for l in lanes]
    plan = {
        "schema": "opentallas.die_plan.v1",
        "note": "S81 72-frame MU release die, plan v2 (PLAN-S81v2 10-23): one 1442.88 x 1226.88 lattice, MY-mirrored "
                "halves, frames as MX r0/r1/r2 bands in E-W 3-frame chains, slices as N-S 1-cell segment chains, svc "
                "2x8 cells, no lane columns. physical/die_plan/s81/gen_plan_v2.py.",
        "die": {"name": "s81", "label": "DeepSeek ROM S81 72-frame MU release die", "tech": "asap7",
                "outline_um": [round(DIE_W, 4), round(DIE_H, 4)], "period_ps": 833, "reach_um": REACH,
                "rep_um": 450.0, "grid_um": G,
                "layer_budget": {"partition_signal_max": "M7", "die_layers": ["M8", "M9"],
                                 "die_use": ["clock_spine", "pg", "ft_reserved"], "cut_avail": {"M8": 0.6, "M9": 0.6}},
                "pg": {"partition_pg_max": "M7", "grid": [
                    {"layer": "M8", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]},
                    {"layer": "M9", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]}]},
                "channels": chans + [
                    {"rect_um": [0, 0, round(DIE_W, 4), X0], "reason": "seal ring"},
                    {"rect_um": [0, round(DIE_H - X0, 4), round(DIE_W, 4), round(DIE_H, 4)], "reason": "seal ring"},
                    {"rect_um": [0, X0, X0, round(DIE_H - X0, 4)], "reason": "seal ring"},
                    {"rect_um": [round(DIE_W - X0, 4), X0, round(DIE_W, 4), round(DIE_H - X0, 4)],
                     "reason": "seal ring"}]},
        "partition_types": out_types,
        "partitions": oparts,
        "ports": oports,
        "lanes": olanes,
        "clock": {"source": {"part": "@die", "bus": "clk"}, "insertion_ps": 250, "insertion_tol_ps": 40,
                  "neighbour_skew_ps": 80, "face_xing": "budgeted",
                  "spine": {"layers": ["M8", "M9"], "root_um": [round(X0 + 11 * PX, 4), round(X0 + 10 * PY, 4)],
                            "topology": "htree"}},
        "reset": {"source": {"part": "@die", "bus": "rst_n"}, "sync_stages": 2, "data_reset": False,
                  "epoch_bit": True, "release": "counted"},
        "budgets": {"face_pins_per_um": 6, "face_pin_layers": 2, "face_window_um": 10, "pin_track_max": 0.6,
                    "cut_ratio_max": 0.6, "cut_step_um": 250},
    }
    out.mkdir(parents=True, exist_ok=True)
    json.dump(plan, open(out / "die_plan.json", "w"), indent=0)
    # ---- metrics ----
    lb, det = [], []
    for lk in lanes:
        cells = routes[lk["id"]]
        lb.append((bends(cells), lk["id"]))
        pids = lane_ports[lk["id"]]
        if not pids:
            continue
        pts = [port_pt(pid) for pid in pids]
        # endpoints: centre of src seg cell face path -> use first/last port points + half-cell legs
        Ln = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))
        man = abs(pts[0][0] - pts[-1][0]) + abs(pts[0][1] - pts[-1][1])
        if len(pids) >= 3 and man > 0:
            det.append((Ln / man, lk["id"]))
    bs = sorted(b for b, _ in lb)
    ds = sorted(d for d, _ in det)

    def pct(v, q):
        return v[min(len(v) - 1, int(math.ceil(q * len(v))) - 1)] if v else 0

    over.sort(reverse=True)
    by_kind = collections.Counter(P[n[0]].kind for n in types.values())
    stats = dict(
        die_um=[round(DIE_W, 2), round(DIE_H, 2)], die_mm2=round(DIE_W * DIE_H / 1e6, 1),
        partitions=len(parts), types=len(types), types_by_kind=dict(by_kind),
        singleton_types=sum(1 for v in types.values() if len(v) == 1),
        lanes=len(lanes), ports=len(ports),
        bends_max=bs[-1], bends_p90=pct(bs, 0.9), bends_hist=dict(collections.Counter(bs)),
        detour_p90=round(pct(ds, 0.9), 3), detour_max=round(ds[-1], 3) if ds else 0,
        detour_worst=sorted(det, reverse=True)[:5],
        face_worst=[dict(a=a, b=b, ratio=round(r, 3), pins=n, len=round(L_, 1)) for r, a, b, k, n, L_ in over[:10]],
        faces_over_06=sum(1 for o in over if o[0] > 0.6 + 1e-9),
        channel_cells=len(chans),
        instances_per_type={tname[k]: len(v) for k, v in types.items()},
    )
    # L1 (COORD 05:34) cell estimate per partition: std cells = std-cell area / 0.136 um2 (ASAP7, measured on a 1.31M-
    # cell synth: 0.178 mm2).  Upper bound = 55 % of the partition's non-hard area as flattened std cells; frame bands
    # use the col_h9 kit inventory (flattened leaves = relay/node/sstn/cfg/qbank/cfifo/rstg ~0.21 mm2 block area per
    # frame at 0.6 fill; ROM macros, rom_elem_q and the closed bf_col stay hard per L1) -> ~0.31 M per band.
    CELL = 0.136e-6
    est = {}
    for p in parts:
        a = p.w * p.h / 1e6
        if p.hard or p.kind in ("phy", "serdes"):
            est[p.name] = (0, "hard")
        elif p.kind == "frame":
            est[p.name] = (int(0.21 * 0.6 / CELL / 3), "frame kit inventory")
        else:
            est[p.name] = (int(0.55 * a / CELL), "upper bound (no leaf synth counts in the plan inputs)")
    kinds = collections.defaultdict(list)
    for p in parts:
        kinds[p.kind].append(est[p.name][0])
    stats["cells_est"] = {k: dict(n=len(v), max=max(v), basis=est[[q.name for q in parts if q.kind == k][0]][1])
                          for k, v in kinds.items()}
    stats["cells_over_1M_ub"] = sum(1 for v in est.values() if v[0] > 1e6)
    json.dump(stats, open(out / "v2_stats.json", "w"), indent=1, default=str)
    json.dump({k: v[0] for k, v in est.items()}, open(out / "cells_est.json", "w"), indent=0)
    json.dump(dict(frames=fmap, type_of=ptype), open(out / "instance_map.json", "w"), indent=0)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asbuilt", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ab = json.load(open(a.asbuilt))
    census = list(csv.DictReader(open(a.census), delimiter="\t"))
    parts, frames, serdes, slices, chans, svcg = build(ab)
    lanes, fmap = lanes_all(ab, census, parts, frames, serdes, slices)
    grid = Grid(parts)
    # every cell covered or a channel
    chan_cells = set()
    for ch in chans:
        x0, y0, x1, y1 = ch["rect_um"]
        for c in range(NC):
            for r in range(NR):
                cx, cy = X0 + (c + .5) * PX, X0 + (r + .5) * PY
                if x0 < cx < x1 and y0 < cy < y1:
                    chan_cells.add((c, r))
    miss = [(c, r) for c in range(NC) for r in range(NR) if (c, r) not in grid.owner and (c, r) not in chan_cells]
    assert not miss, miss
    routes = route(grid, lanes, dict(slices, **svcg))
    stats = emit(parts, lanes, routes, chans, fmap, Path(a.out))
    print(json.dumps({k: v for k, v in stats.items() if k != "instances_per_type"}, indent=1, default=str))


if __name__ == "__main__":
    main()
