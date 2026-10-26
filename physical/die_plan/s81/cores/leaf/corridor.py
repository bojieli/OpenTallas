#!/usr/bin/env python3
"""S81/LEAFPLAN3 r3 10-25: corridor-first leaf placement (fixes r2 PROTO: the rigid one-piece template left the ft
bundles no station-able corridor, ft_sites pushed whole bundles to the W edge strip -> M3/M5 overflow).

1. corridors: every ft bit path in-window -> out-window (straight, or both Manhattan L orders for corner / offset
   slots), rasterised at 8.64 um.  A core (+ FT_HALO + 4.3 um station room) on a path is allowed only as a short run:
   bits ride M6 / M7 over it (bundle density at the windows is <= 4.7 b/um = 0.30 of M6 or M7 alone, inside the 0.6
   budget) and the stations sit in the street on each side, so every merged core run along a path must stay
   <= RUN_MAX (hop 405 incl. the halos).  Cost = bits x (run excess) [hard] + bits x over-core length [soft].
2. the template is split into three rigid groups (internal geometry identical in every type -> intra-group depths
   uniform): A = 4x4 lane block + vn_a/vn_b (+ the tree) + vq + stores; C = vs + vsw + rxsf + rxsb; D = ve_s + ve_m.
   Inter-group links (vq<->vs, stores<->vs, vs<->ve_m, vs<->ve_s) get ONE FIXED station depth (XDEPTH = 1) in all
   types: the search only accepts group offsets whose every inter-group bundle fits 1 station (both hops <= 405 incl.
   the pin spreads).  S-bus types: the whole N-bus-frame placement y-mirrored (as r2).
3. per type: A placed first (top-K by corridor cost + bus term), then C, then D (top-K beams), scored on the union.

usage: corridor.py PLAN_JSON --out PLAN --report JSON [--types t6,t50] [--jobs N]"""
import argparse
import json
import math
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import template as TP  # noqa: E402
V = TP.V
G = V.G
STEP = 4.32
ROOM = V.FT_HALO + 0.5             # halo + rounding: a STREET (3 x 8.64) between two cores is a station site
RUN_MAX = 405.0 - 2 * 4.32        # merged core run a bit may cross between two stations
XDEPTH = 1                        # inter-group bundle station depth, every type
REACH = 405.0
LN = TP.LN
GROUPS = {
    "A": [LN % i for i in range(16)] + ["u_lf.u_vn.u_a", "u_lf.u_vn.u_b", "u_lf.u_vq", "u_lf.u_vp.u_b0",
                                        "u_lf.u_vp.u_b1"],
    "C": ["u_lf.u_vs", "u_lf.u_vsw", "u_lf.u_rxsf", "u_lf.u_rxsb", "u_lf.u_ve.u_s", "u_lf.u_ve.u_m"],
}
GOF = {i: g for g, l in GROUPS.items() for i in l}
STREET = 25.92                    # r3: every core-core gap in the template >= 2 x FT_HALO + a station column (3 x 8.64)


def widen_template(street=STREET):
    """r3 streets: lane channels and the template's 13.8-um core gaps widened to `street` (vn_a / vn_b keep their
    17.28 c_s abutment: 0 stations mandatory; rxsf / rxsb keep 13.8: 0 stations mandatory)"""
    import inspect
    if street is None:
        return
    TP.LP = TP.LANE + street
    TP.CH = street
    src = inspect.getsource(TP.template.__wrapped__ if hasattr(TP.template, "__wrapped__") else TP.template)
    src = src.replace("rfy - 13.8 - rh", "rfy - RXGAP - rh").replace("13.8", "STREETX")
    ns = TP.__dict__
    ns["STREETX"] = street
    ns["RXGAP"] = 13.8
    exec(compile(src, "template_r3", "exec"), ns)
GSEP = 13.8                       # core gap between groups (HC_GAP)


def nframe_slots(T):
    """ft slots in the N-bus frame (S-bus types y-mirrored: N<->S faces, E/W windows mirrored)"""
    W, H = T["outline_um"]
    sbus = {b["face"] for b in T["buses"] if b.get("face") in ("N", "S")} == {"S"}
    out = []
    for s in T.get("ft_slots", []):
        def f(face, win):
            if not sbus:
                return face, win
            if face in ("N", "S"):
                return ("S" if face == "N" else "N"), win
            return face, [H - win[1], H - win[0]]
        fi, wi = f(s["in_face"], s["in_window_um"])
        fo, wo = f(s["out_face"], s["out_window_um"])
        out.append(dict(name=s["name"], fi=fi, wi=wi, fo=fo, wo=wo, bits=s["width"]))
    buses = []
    for b in T["buses"]:
        fb = b["face"]
        if sbus and fb in ("N", "S"):
            fb = "S" if fb == "N" else "N"
        buses.append(dict(b, face=fb))
    return out, sbus, buses


def fpt(face, q, W, H):
    return dict(N=(q, H), S=(q, 0.0), E=(W, q), W=(0.0, q))[face]


def raster(a, b, c):
    """points every STEP along a -> c -> b (Manhattan polyline through corner c)"""
    pts = []
    for p, q in ((a, c), (c, b)):
        L = abs(p[0] - q[0]) + abs(p[1] - q[1])
        n = max(1, int(L / STEP))
        t = np.arange(n) / n
        pts.append(np.stack([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t], 1))
    pts.append(np.array([b]))
    return np.concatenate(pts)


def paths(slots, W, H, K=7):
    """[(bits weight, [order0 points, order1 points])] -- K sample bits per slot"""
    P = []
    for s in slots:
        for k in range(K):
            f = (k + 0.5) / K
            a = fpt(s["fi"], s["wi"][0] + f * (s["wi"][1] - s["wi"][0]), W, H)
            b = fpt(s["fo"], s["wo"][0] + f * (s["wo"][1] - s["wo"][0]), W, H)
            P.append((s["bits"] / K, [raster(a, b, (b[0], a[1])), raster(a, b, (a[0], b[1]))]))
    return P


class Rast:
    """all sample paths padded into one [npath, 2 orders, ncell, 2] array (pad = far away)"""

    def __init__(self, P):
        if not P:                 # a type without ft slots
            P = [(0.0, [np.array([[-1e6, -1e6]]), np.array([[-1e6, -1e6]])])]
        n = max(len(o) for _, os_ in P for o in os_)
        self.w = np.array([w for w, _ in P])
        A = np.full((len(P), 2, n, 2), -1e6)
        for i, (_, os_) in enumerate(P):
            for j, o in enumerate(os_):
                A[i, j, :len(o)] = o
        self.A = A
        self.n = n

    def mask(self, boxes):
        """covered [npath, 2, ncell] for boxes [(x0,y0,x1,y1)] (+ROOM)"""
        m = np.zeros(self.A.shape[:3], bool)
        x, y = self.A[..., 0], self.A[..., 1]
        for b in boxes:
            m |= (x > b[0] - ROOM) & (x < b[2] + ROOM) & (y > b[1] - ROOM) & (y < b[3] + ROOM)
        return m

    def cost(self, m):
        """per path min over orders of 100 x run excess + over-core length; weighted sum"""
        ar = np.arange(m.shape[-1])
        z = np.where(~m, ar, -1)
        lz = np.maximum.accumulate(z, axis=-1)
        run = ((ar - lz).max(-1)) * STEP
        over = m.sum(-1) * STEP
        c = 100.0 * np.maximum(0, run - RUN_MAX) + 0.5 * over
        return float((self.w * c.min(1)).sum()), int((np.maximum(0, run - RUN_MAX).min(1) > 0).sum())


TREE_SHIFT = 3 * 8.64            # r3: tree S sites moved E along their row channel (M -> S hop <= 405 with streets)


def tree_sites_r3(p, lane_off):
    M, S = TP._tree_sites_r2(p, lane_off)
    return M, {k: (round(v[0] + TREE_SHIFT, 3), v[1]) for k, v in S.items()}


if not hasattr(TP, "_tree_sites_r2"):
    TP._tree_sites_r2 = TP.tree_sites
    TP.tree_sites = tree_sites_r3


def template_groups():
    widen_template()
    p, sz, bb, lane_off = TP.template()
    rel, gbox = {}, {}
    for g, l in GROUPS.items():
        x0 = min(p[i][0] for i in l)
        y0 = min(p[i][1] for i in l)
        rel[g] = {i: (round(p[i][0] - x0, 4), round(p[i][1] - y0, 4)) for i in l}
        gbox[g] = (max(rel[g][i][0] + sz[i][0] for i in l), max(rel[g][i][1] + sz[i][1] for i in l))
    org = {g: (min(p[i][0] for i in l), min(p[i][1] for i in l)) for g, l in GROUPS.items()}
    return p, sz, lane_off, rel, gbox, org


def gboxes(g, xy, rel, sz):
    return [(xy[0] + rel[g][i][0], xy[1] + rel[g][i][1], xy[0] + rel[g][i][0] + sz[i][0],
             xy[1] + rel[g][i][1] + sz[i][1]) for i in GROUPS[g]]


def centre(g, i, xy, rel, sz):
    return (xy[0] + rel[g][i][0] + sz[i][0] / 2, xy[1] + rel[g][i][1] + sz[i][1] / 2)


LINKS = [("A", "u_lf.u_vq", "C", "u_lf.u_vs"), ("A", "u_lf.u_vp.u_b0", "C", "u_lf.u_vs"),
         ("A", "u_lf.u_vp.u_b1", "C", "u_lf.u_vs"), ("D", "u_lf.u_ve.u_m", "C", "u_lf.u_vs"),
         ("D", "u_lf.u_ve.u_s", "C", "u_lf.u_vs")]
LINK_SLACK = 50.0                 # room for the station's push-out of a halo


def link_table(T0, p, sz, rel, org):
    """inter-group core<->core bundles of the template on an N-bus type: [(group a, rel a, group b, rel b, spreads)]"""
    o, sbus = TP.place_type(T0, p, sz, None, 0.0, 0.0)
    assert not sbus
    pg = {c["inst"]: V._placed_groups(c) for c in o}
    out = []
    for e in TP.other_entries(T0, o):
        if not e["conn"].startswith("core:"):
            continue
        a = e["conn"].split("|")[0][5:].rsplit(".", 1)
        b = e["conn"].split("|")[1][5:]
        ga, gb = GOF.get(a[0]), GOF.get(b)
        if ga == gb:
            continue
        pa = pg[a[0]][1].get(a[1])
        cb = e.get("capture", "")
        pb = pg[b][1].get(cb.rsplit(".", 1)[1]) if cb.startswith(b + ".") else None
        sa, sb = (pa[4] if pa else 0.0), (pb[4] if pb else 0.0)
        fa = (e["from_um"][0] - org[ga][0], e["from_um"][1] - org[ga][1])
        fb = (e["to_um"][0] - org[gb][0], e["to_um"][1] - org[gb][1])
        out.append((ga, fa, gb, fb, sa + sb, e["conn"]))
    return out


def sep_ok(ba, bb):
    """every core of one group >= GSEP from every core of the other (station street between groups)"""
    a = np.array(ba)[:, None, :]
    b = np.array(bb)[None, :, :]
    g = np.maximum.reduce([b[..., 0] - a[..., 2], a[..., 0] - b[..., 2], b[..., 1] - a[..., 3], a[..., 1] - b[..., 3]])
    return bool((g >= GSEP - 1e-6).all())


def search(T, rel, sz, gbox, lt, org, beam=10, win=8):
    """joint search: A anywhere on the 17.28 grid, C within +-win x 17.28 of its template offset from A; corridor
    cost on the union; then the G0C face rule (0 faces away) on the best candidates"""
    W, H = T["outline_um"]
    slots, sbus, buses = nframe_slots(T)
    R = Rast(paths(slots, W, H))
    E = V.HC_EDGE_UM + 0.2
    bw = [b for b in buses if b["face"] == "N"]
    bx = np.mean([sum(b["window_um"]) / 2 for b in bw]) if bw else W / 2
    vnx = rel["A"]["u_lf.u_vn.u_a"][0]
    d0 = (org["C"][0] - org["A"][0], org["C"][1] - org["A"][1])

    def busterm(pl):
        c = centre("C", "u_lf.u_vs", pl["C"], rel, sz)
        t = 1265 * (abs(c[0] - bx) + (H - c[1]))
        c = centre("A", "u_lf.u_vq", pl["A"], rel, sz)
        return t + 668 * (abs(c[0] - bx) + (H - c[1]))

    def links_ok(pl):
        for ga, fa, gb, fb, spr, _ in lt:
            L = abs(pl[ga][0] + fa[0] - pl[gb][0] - fb[0]) + abs(pl[ga][1] + fa[1] - pl[gb][1] - fb[1])
            if L + spr > (XDEPTH + 1) * REACH - LINK_SLACK:
                return False
        return True

    def inside(g, xy):
        return E <= xy[0] and xy[0] + gbox[g][0] <= W - E and E <= xy[1] and xy[1] + gbox[g][1] <= H - E
    cm = {}

    def cmask(xy):
        if xy not in cm:
            cm[xy] = R.mask(gboxes("C", xy, rel, sz))
        return cm[xy]
    cand = []
    xs = np.arange(E, W - E - gbox["A"][0] + 1e-6, 2 * G)
    ys = np.arange(E, H - E - gbox["A"][1] + 1e-6, 2 * G)
    for ax in xs:
        for ay in ys:
            A = (round(float(ax), 4), round(float(ay), 4))
            mA = None
            for i in range(-win, win + 1):
                for j in range(-2 * win, 2 * win + 1):
                    Cxy = (round(A[0] + d0[0] + i * 2 * G, 4), round(A[1] + d0[1] + j * 2 * G, 4))
                    if Cxy[0] < A[0] + vnx or not inside("C", Cxy):
                        continue
                    pl = {"A": A, "C": Cxy}
                    if not links_ok(pl) or not sep_ok(gboxes("A", A, rel, sz), gboxes("C", Cxy, rel, sz)):
                        continue
                    if mA is None:
                        mA = R.mask(gboxes("A", A, rel, sz))
                    c, v = R.cost(mA | cmask(Cxy))
                    cand.append((c + busterm(pl), pl, v, c))
    cand.sort(key=lambda t: t[0])
    nfa = {}

    def faces(pl):
        pt = {i: (pl[g][0] + rel[g][i][0], pl[g][1] + rel[g][i][1]) for g in pl for i in GROUPS[g]}
        o, _ = TP.place_type(T, pt, sz, None, 0.0, 0.0)
        # the dn-bus ports on the vn W face end in a FIRM chain whose last station is in the lane / vn channel
        # (TP.w_face_bus): G0C takes that station as the partner direction, so they are not counted here
        cc = V.CORE_CONNS["leaf"]
        save = {h: {k: cc[h].pop(k) for k in ("rb_v", "rb_d", "n_go", "n_pre") if k in cc[h]}
                for h in ("u_lf.u_vn.u_a", "u_lf.u_vn.u_b")}
        try:
            return V.core_faces_away("leaf", o, W, H, T["buses"]), TP.legal(o, W, H)
        finally:
            for h, d in save.items():
                cc[h].update(d)
    for t in cand[:600]:
        f_, lg = faces(t[1])
        nfa[f_] = nfa.get(f_, 0) + 1
        if f_ == 0 and lg:
            return dict(pl=t[1], cost=round(t[3], 1), score=round(t[0], 1), viol_paths=t[2], sbus=sbus,
                        ncand=len(cand), faces_hist=nfa)
    print(T.get("module"), "no candidate; faces histogram", nfa, "ncand", len(cand), flush=True)
    return None


def one_site(fr, to, hb, W, H, sa, sb):
    """the single inter-group station: best point (max hop minimal) among both L paths' samples, pushed outside"""
    best = None
    for c in ((to[0], fr[1]), (fr[0], to[1])):
        pts = raster(fr, to, c)
        for p in pts[::2]:
            q = V._outside(float(p[0]), float(p[1]), hb, W, H)
            h1 = abs(fr[0] - q[0]) + abs(fr[1] - q[1]) + sa
            h2 = abs(q[0] - to[0]) + abs(q[1] - to[1]) + sb
            k = max(h1, h2)
            if best is None or k < best[0]:
                best = (k, q)
    return best


def build(T, res, p, sz, lane_off, rel, org):
    """hard_cores + internal_stations of one type from the group offsets"""
    W, H = T["outline_um"]
    pl = res["pl"]
    pt = {}
    for g, xy in pl.items():
        for i in GROUPS[g]:
            pt[i] = (round(xy[0] + rel[g][i][0], 4), round(xy[1] + rel[g][i][1], 4))
    o, sbus = TP.place_type(T, pt, sz, lane_off, 0.0, 0.0)
    M, S = TP.tree_sites(p, lane_off)
    sh = (pl["A"][0] - org["A"][0], pl["A"][1] - org["A"][1])
    tree = TP.tree_entries(T, o, M, S, sbus, sh[0], sh[1])
    oth = TP.w_face_bus(T, o, TP.other_entries(T, o), tree[0]["regs_um"][0] if tree else None)
    hb = [(b[0] - V.FT_HALO, b[1] - V.FT_HALO, b[2] + V.FT_HALO, b[3] + V.FT_HALO) for b in TP.boxes(o).values()]
    pg = {c["inst"]: V._placed_groups(c) for c in o}
    bad = []
    for e in oth:
        if not e["conn"].startswith("core:"):
            continue
        a = e["conn"].split("|")[0][5:].rsplit(".", 1)
        b = e["conn"].split("|")[1][5:]
        if GOF.get(a[0]) == GOF.get(b):
            continue
        ga = pg[a[0]][1].get(a[1])
        cb = e.get("capture", "")
        gb = pg[b][1].get(cb.rsplit(".", 1)[1]) if cb.startswith(b + ".") else None
        sa, sb = (ga[4] if ga else 0.0), (gb[4] if gb else 0.0)
        k, q = one_site(e["from_um"], e["to_um"], hb, W, H, sa, sb)
        e["regs_um"] = [[round(q[0], 3), round(q[1], 3)]]
        e["note"] = "LEAFPLAN3 r3: inter-group bundle, fixed depth %d in every type (max hop %.1f um incl. pin spread)" % (
            XDEPTH, k)
        if k > REACH + 1e-6:
            bad.append((e["conn"], round(k, 1)))
    T["hard_cores"] = o
    T["internal_stations"] = tree + oth
    return dict(offsets=pl, sbus=sbus, xgroup_bad=bad,
                faces_away=V.core_faces_away("leaf", o, W, H, T["buses"]), legal=TP.legal(o, W, H),
                max_hop=round(max(max(TP.hops(e)) for e in tree + oth), 2),
                depth={e["conn"] + ("" if e["conn"].startswith("core:") else "->" + e["capture"]): len(e["regs_um"])
                       for e in oth})


def work(args):
    tn, T, T0 = args
    p, sz, lane_off, rel, gbox, org = template_groups()
    lt = link_table(T0, p, sz, rel, org)
    r = search(T, rel, sz, gbox, lt, org)
    if r is None:
        return tn, None, None
    info = build(T, r, p, sz, lane_off, rel, org)
    info.update(cost=r["cost"], score=r["score"], viol_paths=r["viol_paths"], ncand=r["ncand"])
    return tn, info, dict(hard_cores=T["hard_cores"], internal_stations=T["internal_stations"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--report")
    ap.add_argument("--types")
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    P = json.load(open(a.plan))
    sel = a.types.split(",") if a.types else None
    todo = [(tn, T) for tn, T in P["partition_types"].items()
            if tn.startswith("ot_s81sl_leaf__t") and (not sel or tn.split("__")[1] in sel)]
    T0 = P["partition_types"]["ot_s81sl_leaf__t1"]
    todo = [(tn, T, T0) for tn, T in todo]
    p, sz, lane_off, rel, gbox, org = template_groups()
    rep = dict(groups={g: dict(insts=l, bbox=[round(v, 2) for v in gbox[g]]) for g, l in GROUPS.items()},
               xdepth=XDEPTH, run_max=RUN_MAX, types={})
    with Pool(a.jobs) as pool:
        for tn, info, upd in pool.imap_unordered(work, todo):
            rep["types"][tn] = info
            if upd:
                P["partition_types"][tn].update(upd)
            print(tn, None if info is None else {k: v for k, v in info.items() if k not in ("depth",)}, flush=True)
    # uniform depth table: every core<->core class must have one depth in every type
    cls = {}
    for tn, info in rep["types"].items():
        for k, d in (info or {}).get("depth", {}).items():
            if k.startswith("core:"):
                cls.setdefault(k, set()).add(d)
    rep["depth_table"] = {k: sorted(v) for k, v in sorted(cls.items())}
    rep["nonuniform"] = {k: sorted(v) for k, v in cls.items() if len(v) > 1}
    print("nonuniform classes:", rep["nonuniform"])
    if a.out:
        Path(a.out).write_text(json.dumps(P, indent=0) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
