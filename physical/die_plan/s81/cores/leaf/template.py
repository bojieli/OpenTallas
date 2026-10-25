#!/usr/bin/env python3
"""S81/LEAFPLAN3 10-25: one fixed leaf template for all 72 leaf types (GEOM-REVIEW 03:33 LEAFPLAN2 FAIL fix).

GEOM recipe: vn_a / vn_b abutted on their c_s faces (one W data face), the 16 hcpl lanes as a 4 x 4 block abutting that
face (row k = lanes 4k..4k+3, column i = lane 4k+i: bit order -- hw_d[(4k+i)*16 +: 16], the hq_d 64-b group of column
i is broadcast to the 4 lanes of the column), one registered broadcast tree per lane bus with stations only in
inter-lane channels (hops <= 405 um, no crossings), vq / stores / vs / ve / vsw / rx E of vn, empty quadrants
compacted.  The relative arrangement and the orientations are identical in every type: per type only the template's
translation (y offset, N-bus frame) and the bus-face y mirror (S-bus types, every core MX) change, so every core <->
core distance -- and so every internal station count -- is the same in all 72 types (uniform station-depth table,
static schedule).  Deterministic: no annealing.

usage: template.py PLAN_JSON [--out PLAN_JSON] [--report JSON] [--types t6,t50]
"""
import argparse
import copy
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
S81 = HERE.parents[1]
sys.path.insert(0, str(S81))
import gen_plan_v4 as V  # noqa: E402

G = V.G
LANE = 114.48
LP = 129.6                      # lane pitch: 114.48 + 15.12 channel (>= HC_GAP 13.8, 8.64 lattice)
CH = LP - LANE
LN = "u_lf.u_vp.g_ln[%d].u_l"
# template frame (N-bus frame, x from the W end of the lane block, y from the lane block's S edge); origins on the
# 8.64 lattice; cores keep >= HC_GAP_UM (13.8) facing gaps


def up(v):
    return math.ceil(round(v / G, 6)) * G


def dn(v):
    return math.floor(round(v / G, 6)) * G


def template():
    """{inst: (x, y)} template-frame origins, core sizes, bbox, lane-block offset.  LEAFPLAN3 r2 (COORD 10-25: face
    rule by layout, closed pin tables kept, R0 only):
      lane block 4 x 4 | vn_a / vn_b stack (W data face, c_s abutted) | vs (level with vn_b) | vsw E of vs (level:
      its N i_* and S o_* faces both see vs side-on);  above vn: ve_s (E part), ve_m above vs; below vn_a's E half: vq (ve_s E
      m_* faces ve_m W m_*);  below vn_a: the 2 store SRAMs (W part: vn wl / n_* W face and vs x_* W face both look
      at them);  below vs: rxsf over rxsb, centred under vs (rxsf E i_x / W o_* and rxsb E i_* / W o_r side-on to
      vs above them)."""
    sz = {}
    for c in V.NONFRAME_HC["leaf"]["cores"]:
        sz[c["inst"]] = V._lef_size(c["lef"]) if not c.get("outline") else c["outline"]
    p = {}
    for k in range(4):
        for i in range(4):
            p[LN % (4 * k + i)] = (i * LP, k * LP)
    blk = 3 * LP + LANE                                   # 503.28
    gap = 17.28
    vnx = up(blk + 13.8)
    vna_h, vnb_h = sz["u_lf.u_vn.u_a"][1], sz["u_lf.u_vn.u_b"][1]
    vn_w = sz["u_lf.u_vn.u_a"][0]
    stack = vna_h + gap + vnb_h
    vny = dn(blk / 2 - stack / 2)
    p["u_lf.u_vn.u_a"] = (vnx, vny)
    vnby = round(vny + vna_h + gap, 4)
    p["u_lf.u_vn.u_b"] = (vnx, vnby)
    vntop = vnby + vnb_h
    vsx = up(vnx + vn_w + 13.8)
    vs_w, vs_h = sz["u_lf.u_vs"]
    vsy = dn(vntop - vs_h)                                # level with vn_b
    p["u_lf.u_vs"] = (vsx, vsy)
    vsw_w, vsw_h = sz["u_lf.u_vsw"]
    p["u_lf.u_vsw"] = (up(vsx + vs_w + 13.8), dn(vsy + vs_h / 2 - vsw_h / 2))
    # above vn: ve block (ve_s | ve_m, 181.44 offset) with ve_m over vs; vq W of ve_s
    vey = up(max(vntop, vsy + vs_h) + 13.8)
    p["u_lf.u_ve.u_m"] = (vsx, vey)
    p["u_lf.u_ve.u_s"] = (round(vsx - 181.44, 4), vey)
    vq_w, vq_h = sz["u_lf.u_vq"]
    # vq below vn_a's E half: vn E y and vq W y / E u / N xf all see their partners
    p["u_lf.u_vq"] = (round(vsx - 181.44, 4), dn(vny - 13.8 - vq_h))
    # below vn_a: stores (W part of vn)
    st_w, st_h = sz["u_lf.u_vp.u_b0"]
    b1y = dn(vny - 13.8 - st_h)
    p["u_lf.u_vp.u_b1"] = (vnx, b1y)
    p["u_lf.u_vp.u_b0"] = (vnx, dn(b1y - 13.8 - st_h))
    # below vs: rxsf then rxsb, centred under vs
    rw, rh = sz["u_lf.u_rxsf"]
    rx_x = dn(vsx + vs_w / 2 - rw / 2)
    rfy = dn(vsy - 13.8 - rh)
    p["u_lf.u_rxsf"] = (rx_x, rfy)
    p["u_lf.u_rxsb"] = (rx_x, dn(rfy - 13.8 - rh))
    x0 = min(v[0] for v in p.values())
    y0 = min(v[1] for v in p.values())
    p = {k_: (round(v[0] - x0, 4), round(v[1] - y0, 4)) for k_, v in p.items()}
    bw = max(p[k_][0] + sz[k_][0] for k_ in p)
    bh = max(p[k_][1] + sz[k_][1] for k_ in p)
    return p, sz, (bw, bh), (-x0, -y0)


def tree_sites(p, lane_off):
    """broadcast / gather tree sites in the template frame: M = merge / fan-out site in the channel between the lane
    block and the vn W face at the vn stack centre; S_l / S_u = the lower / upper half sites at the crossings of the
    centre column channel with the row-0/1 and row-2/3 channels."""
    lx, ly = lane_off
    blk = 3 * LP + LANE
    vnx = p["u_lf.u_vn.u_a"][0]
    vna, vnb = p["u_lf.u_vn.u_a"][1], p["u_lf.u_vn.u_b"][1]
    cy = (vna + vnb + 172.8) / 2
    M = (round((lx + blk + vnx) / 2, 3), round(cy, 3))
    xc = lx + 2 * LP - CH / 2
    S = {"l": (round(xc, 3), round(ly + LP - CH / 2, 3)), "u": (round(xc, 3), round(ly + 3 * LP - CH / 2, 3))}
    return M, S



H_OUT = ["hq_v", "hq_d"]                                  # vn -> lanes (broadcast): vn port -> M -> S -> lane W face
H_IN = ["hw_v", "hw_j", "hw_hf", "hw_d", "hr_v", "hr_j", "hr_hf"]   # lanes / vp -> vn (gather): lane E face -> S -> M -> vn
PITCH_H, PITCH_V = 0.064, 0.064                           # M6 (H) / M7 (V): the only layers over hard cores
RATIO_MAX = 0.6


def place_type(T, p, sz, off, xoff, yoff):
    """hard_cores[] of one type: template p translated by (xoff, yoff) in the N-bus frame, y-mirrored (MX) for S-bus
    types (exact mirror about the type centre line, then snapped down to the 8.64 lattice as gen_plan_v4.mirrored)."""
    W, H = T["outline_um"]
    sbus = {b["face"] for b in T["buses"] if b.get("face") in ("N", "S")} == {"S"}
    byi = {c["inst"]: c for c in V.NONFRAME_HC["leaf"]["cores"]}
    dx, dy = V.CORE_TRACK_OFFSET
    out = []
    for inst, (x, y) in p.items():
        c = byi[inst]
        cw, ch = sz[inst]
        x_, y_ = round(x + xoff, 4), round(y + yoff, 4)
        orient, to = "R0", list(V.CORE_TRACK_OFFSET)
        if sbus:
            y_ = math.floor(round((H - (y_ + dy + ch) - dy) / G, 6)) * G
            orient = "MX"
            to[1] = round((0.036 - ch) % 0.048, 4)
        e = V._core_view(V.NONFRAME_HC["leaf"], c, None, origin_um=[round(x_, 4), round(y_, 4)], outline_um=[cw, ch],
                         orient=orient, track_offset_um=to)
        out.append(e)
    order = {c["inst"]: i for i, c in enumerate(T["hard_cores"])}
    out.sort(key=lambda e: order.get(e["inst"], 99))
    return out, sbus


def legal(o, W, H):
    bx = [(c["origin_um"][0] + c["track_offset_um"][0], c["origin_um"][1] + c["track_offset_um"][1],
           c["origin_um"][0] + c["track_offset_um"][0] + c["outline_um"][0],
           c["origin_um"][1] + c["track_offset_um"][1] + c["outline_um"][1]) for c in o]
    E = V.HC_EDGE_UM
    if any(b[0] < E - 1e-6 or b[1] < E - 1e-6 or b[2] > W - E + 1e-6 or b[3] > H - E + 1e-6 for b in bx):
        return False
    for i, a in enumerate(bx):
        for b in bx[i + 1:]:
            if max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3]) < V.HC_GAP_UM - 1e-6:
                return False
    return True


def boxes(o):
    return {c["inst"]: (c["origin_um"][0] + c["track_offset_um"][0], c["origin_um"][1] + c["track_offset_um"][1],
                        c["origin_um"][0] + c["track_offset_um"][0] + c["outline_um"][0],
                        c["origin_um"][1] + c["track_offset_um"][1] + c["outline_um"][1]) for c in o}


def _fpt(face, win, W, H):
    m = sum(win) / 2
    return dict(N=(m, H), S=(m, 0.0), E=(W, m), W=(0.0, m))[face]


def _seg_cross(a, b, bx):
    """cores whose interior a horizontal / vertical segment a-b crosses: [(inst, 'H'|'V', perpendicular extent)]"""
    r = []
    if abs(a[1] - b[1]) < 1e-9:
        y, x0, x1 = a[1], min(a[0], b[0]), max(a[0], b[0])
        for k, (p0, q0, p1, q1) in bx.items():
            if q0 < y < q1 and x0 < p1 and x1 > p0:
                r.append((k, "H", q1 - q0))
    else:
        x, y0, y1 = a[0], min(a[1], b[1]), max(a[1], b[1])
        for k, (p0, q0, p1, q1) in bx.items():
            if p0 < x < p1 and y0 < q1 and y1 > q0:
                r.append((k, "V", p1 - p0))
    return r


def overcore(T, o):
    """COORD 01:00 over-core ft rule, per bit: every ft bit's path in-window pin -> its exact station sites
    (bit_sites_um) -> out-window pin, each leg on the better of its two Manhattan L orders (as ft_sites._visible); the
    bits of one slot that cross one hard core on one layer: bits / (core extent across the leg / M6 or M7 pitch) <= 0.6.
    Also station sites inside a core.  Slots without bit sites fall back to the centroid legs (whole bundle).
    Returns (worst ratio, [fails], [stations inside cores])."""
    import numpy as np
    W, H = T["outline_um"]
    bx = boxes(o)
    names = list(bx)
    B = np.array([bx[k] for k in names])
    worst, fails, inside = 0.0, [], []

    def wpts(face, win, n, order):
        t = (np.arange(n) + 0.5) / n
        if order == "lsb_high":
            t = t[::-1]
        q = win[0] + t * (win[1] - win[0])
        if face in ("N", "S"):
            return np.stack([q, np.full(n, H if face == "N" else 0.0)], 1)
        return np.stack([np.full(n, W if face == "E" else 0.0), q], 1)

    def cross(a, b):
        """[nbits, ncores] bool: H segment a->b' then V b'->b (xy order) crossing core interiors; and the yx order"""
        res = []
        for xy in (True, False):
            c = np.stack([b[:, 0], a[:, 1]], 1) if xy else np.stack([a[:, 0], b[:, 1]], 1)
            h0, h1 = (a, c) if xy else (c, b)
            v0, v1 = (c, b) if xy else (a, c)
            y = h0[:, 1:2]; xl = np.minimum(h0[:, 0:1], h1[:, 0:1]); xh = np.maximum(h0[:, 0:1], h1[:, 0:1])
            hit_h = (B[None, :, 1] < y) & (y < B[None, :, 3]) & (xl < B[None, :, 2]) & (xh > B[None, :, 0])
            x = v0[:, 0:1]; yl = np.minimum(v0[:, 1:2], v1[:, 1:2]); yh = np.maximum(v0[:, 1:2], v1[:, 1:2])
            hit_v = (B[None, :, 0] < x) & (x < B[None, :, 2]) & (yl < B[None, :, 3]) & (yh > B[None, :, 1])
            res.append((hit_h, hit_v))
        # per bit the order with fewer crossed cores (ft_sites keeps a visible order when one exists)
        n0 = res[0][0].sum(1) + res[0][1].sum(1)
        n1 = res[1][0].sum(1) + res[1][1].sum(1)
        pick = (n1 < n0)[:, None]
        return np.where(pick, res[1][0], res[0][0]), np.where(pick, res[1][1], res[0][1])
    for s in T.get("ft_slots", []):
        sites = s.get("bit_sites_um")
        n = s["width"] + 1
        if sites and all(len(st) == n for st in sites):
            stages = [np.array(st, dtype=float) for st in sites]
        else:
            stages = [np.repeat(np.array([r], dtype=float), n, 0) for r in s.get("regs_um", [])]
        pts = [wpts(s["in_face"], s["in_window_um"], n, s.get("order"))] + stages + \
              [wpts(s["out_face"], s["out_window_um"], n, s.get("order"))]
        for st in stages:
            ins = (B[None, :, 0] < st[:, 0:1]) & (st[:, 0:1] < B[None, :, 2]) & (B[None, :, 1] < st[:, 1:2]) & \
                  (st[:, 1:2] < B[None, :, 3])
            for j in np.flatnonzero(ins.any(0)):
                inside.append((s["name"], names[j], int(ins[:, j].sum())))
        hh = np.zeros(len(names)); vv = np.zeros(len(names))
        for a, b in zip(pts, pts[1:]):
            h, v = cross(a, b)
            hh = np.maximum(hh, h.sum(0)); vv = np.maximum(vv, v.sum(0))
        for j, k in enumerate(names):
            for cnt, d, ext in ((hh[j], "H", B[j, 3] - B[j, 1]), (vv[j], "V", B[j, 2] - B[j, 0])):
                if cnt <= 0:
                    continue
                r = cnt / (ext / (PITCH_H if d == "H" else PITCH_V))
                worst = max(worst, r)
                if r > RATIO_MAX:
                    fails.append(dict(slot=s["name"], core=k, layer="M6" if d == "H" else "M7", bits=int(cnt),
                                      ratio=round(float(r), 3)))
    return round(float(worst), 3), fails, inside


def band_score(T, o):
    """placement-time estimate (stations are re-sited by ft_sites afterwards): every straight ft slot's corridor band
    (its window, across the whole partition) over a core whose extent across the band would carry the full bundle
    above 0.6 of the M6 / M7 tracks."""
    W, H = T["outline_um"]
    bx = boxes(o)
    n = 0
    for s in T.get("ft_slots", []):
        f = {s["in_face"], s["out_face"]}
        for k, (p0, q0, p1, q1) in bx.items():
            if f == {"E", "W"}:
                lo, hi = min(s["in_window_um"][0], s["out_window_um"][0]), max(s["in_window_um"][1], s["out_window_um"][1])
                if q0 < hi and q1 > lo and s["width"] / ((q1 - q0) / PITCH_H) > RATIO_MAX:
                    n += 1
            elif f == {"N", "S"}:
                lo, hi = min(s["in_window_um"][0], s["out_window_um"][0]), max(s["in_window_um"][1], s["out_window_um"][1])
                if p0 < hi and p1 > lo and s["width"] / ((p1 - p0) / PITCH_V) > RATIO_MAX:
                    n += 1
    return n


def tree_entries(T, o, M, S, sbus, xoff, yoff):
    """internal_stations[] of the vn <-> lane buses: one registered tree per port (2 levels: M at the vn face channel,
    S_l / S_u at the lane-block channel crossings); every (vn half, port, lane) link listed (G0C R3-INTERNAL coverage),
    sites shared."""
    W, H = T["outline_um"]

    def tf(pt):
        x, y = pt[0] + xoff, pt[1] + yoff
        return [round(x, 3), round(H - y if sbus else y, 3)]
    Mt = tf(M)
    St = {k: tf(v) for k, v in S.items()}
    pl = {c["inst"]: V._placed_groups(c) for c in o}
    ents = []
    for h in "ab":
        vi = "u_lf.u_vn.u_" + h
        for port in H_OUT + H_IN:
            g = pl[vi][1].get(port)
            if not g:
                continue
            for ln in range(16):
                li = LN % ln
                lg = pl[li][1]
                # lane end: W face inputs (r0..r3) for the broadcast, E face output (o) for the gather
                q = lg["r1"] if port in H_OUT else lg["o"]
                lp = [round(q[0], 3), round(q[1], 3)]
                half = "l" if ln < 8 else "u"
                vp = [round(g[0], 3), round(g[1], 3)]
                if port in H_OUT:
                    fr, to, regs = vp, lp, [Mt, St[half]]
                    launch, cap = "core:%s.%s" % (vi, port), li
                else:
                    fr, to, regs = lp, vp, [St[half], Mt]
                    launch, cap = li, "%s.%s" % (vi, port)
                ents.append(dict(conn="core:%s.%s|core:%s" % (vi, port, li), from_um=fr, to_um=to, regs_um=regs,
                                 bits=g[2], launch=launch, capture=cap,
                                 note="LEAFPLAN3 tree %s: %s -> M -> S_%s -> %s (shared sites; template depth 2)" % (
                                     "broadcast" if port in H_OUT else "gather", vi.split(".")[-1] + "." + port,
                                     half, "lane %d" % ln)))
    return ents


def other_entries(T, o):
    """every other declared core_conns bundle: gen_plan_v4.core_internal_stations on the template placement with the
    vn <-> lane ports taken out (they are the tree above)"""
    W, H = T["outline_um"]
    cc = V.CORE_CONNS["leaf"]
    save = copy.deepcopy(cc)
    try:
        for h in "ab":
            vi = "u_lf.u_vn.u_" + h
            for port in H_OUT + H_IN:
                cc[vi].pop(port, None)
        ents, cyc = V.core_internal_stations("leaf", o, W, H, T["buses"])
    finally:
        cc.clear()
        cc.update(save)
    return ents


def w_face_bus(T, o, ents, mt):
    """dn-bus ports on the vn halves' W face (rb_*, n_go, n_pre): their FIRM chain ends in the lane-block / vn channel
    in front of the pin (the M channel), so the last register sits W of the face (G0C face rule: the bus reaches the
    core from its last station) and the wire comes round the stack in the channel, not over vn."""
    if mt is None:
        return ents
    W, H = T["outline_um"]
    hb = [(b[0] - V.FT_HALO, b[1] - V.FT_HALO, b[2] + V.FT_HALO, b[3] + V.FT_HALO) for b in boxes(o).values()]
    out = []
    for e in ents:
        cap = e.get("capture", "")
        if not (e["conn"].startswith("bus:") and cap.startswith("u_lf.u_vn.") and
                cap.rsplit(".", 1)[1] in ("rb_v", "rb_d", "n_go", "n_pre")):
            out.append(e)
            continue
        fr, to = e["from_um"], e["to_um"]
        C = (mt[0], to[1])
        L = abs(fr[0] - C[0]) + abs(fr[1] - C[1])
        n = max(0, math.ceil(L / 400.0) - 1)
        for _ in range(12):
            regs = [V._outside(fr[0] + (C[0] - fr[0]) * j / (n + 1), fr[1] + (C[1] - fr[1]) * j / (n + 1), hb, W, H)
                    for j in range(1, n + 1)] + [C]
            pts = [fr] + regs + [to]
            if max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])) <= 405.0:
                break
            n += 1
        e = dict(e, regs_um=[[round(x, 3), round(y, 3)] for x, y in regs])
        e["note"] = "LEAFPLAN3: dn bus -> vn W-face port, last FIRM station in the lane-block / vn channel: %d station(s)" % len(regs)
        out.append(e)
    return out


def hops(e):
    pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
    return [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]


def run(plan, types=None):
    p, sz, (bw, bh), lane_off = template()
    M, S = tree_sites(p, lane_off)
    rep = dict(template=dict(origins=p, bbox=[round(bw, 3), round(bh, 3)], tree_M=M, tree_S=S), types={})
    E = V.HC_EDGE_UM
    for tn, T in plan["partition_types"].items():
        if not tn.startswith("ot_s81sl_leaf__t") or (types and tn.split("__")[1] not in types):
            continue
        W, H = T["outline_um"]
        best = None
        xs = [round(E + G * i, 4) for i in range(0, 20) if E + G * i + bw + 0.2 <= W - E]
        ys = [round(E + G * j, 4) for j in range(0, 200) if E + G * j + bh + 0.2 <= H - E]
        k0 = [s_["stations"] for s_ in T["ft_slots"]]
        for xo in xs:
            for yo in ys:
                o, sbus = place_type(T, p, sz, lane_off, xo, yo)
                if not legal(o, W, H):
                    continue
                fa = V.core_faces_away("leaf", o, W, H, T["buses"])
                if best is not None and fa > best[0][0]:
                    continue
                bs = band_score(T, o)
                # G0C face rule first, then the ft band estimate, then the template's N side (bus ports) toward
                # the bus face (N-bus frame: larger y offset = nearer the bus in N and S types alike)
                key = (fa, bs, -(yo), xo)
                if best is None or key < best[0]:
                    best = (key, o, sbus, xo, yo)
        key, o, sbus, xo, yo = best
        ft_add = sum(max(0, V.ft_stations_macro(s_, o, W, H, smax=V.FT_KIT_REACH_UM * 0.98) -
                         V.ft_stations_macro(s_, [dict(origin_um=[-1e6, -1e6], outline_um=[1, 1])], W, H,
                                             smax=V.FT_KIT_REACH_UM * 0.98)) for s_ in T["ft_slots"])
        tree = tree_entries(T, o, M, S, sbus, xo, yo)
        oth = w_face_bus(T, o, other_entries(T, o), tree[0]["regs_um"][0] if tree else None)
        T["hard_cores"] = o
        T["internal_stations"] = tree + oth
        cls = {}
        for e in oth:
            a, _, b = e["conn"].partition("|")
            ka = a.rsplit(".", 1)[0] if a.startswith("core:") else a
            cls.setdefault("%s|%s" % (e["conn"].split("|")[0], e.get("capture", "")), len(e["regs_um"]))
        rep["types"][tn] = dict(offset=[xo, yo], sbus=sbus, faces_away=V.core_faces_away("leaf", o, W, H, T["buses"]), band_overcore=key[1], ft_macro_added=ft_add,
                                tree_entries=len(tree), other_entries=len(oth),
                                max_hop=round(max(max(hops(e)) for e in tree + oth), 2),
                                other_depth={e["conn"] + ("" if e["conn"].startswith("core:") else "->" + e["capture"]):
                                             len(e["regs_um"]) for e in oth})
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--report")
    ap.add_argument("--types")
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    rep = run(plan, a.types.split(",") if a.types else None)
    if a.out:
        Path(a.out).write_text(json.dumps(plan, indent=0) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    for tn, r in rep["types"].items():
        print(tn, r["offset"], "S" if r["sbus"] else "N", "band", r["band_overcore"], "ftadd", r["ft_macro_added"],
              "maxhop", r["max_hop"], "faces", r["faces_away"], "oth", r["other_entries"])


if __name__ == "__main__":
    main()
