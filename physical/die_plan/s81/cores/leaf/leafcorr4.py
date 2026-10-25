#!/usr/bin/env python3
"""S81/LEAF4 10-25: corridor-first leaf placement, hard-core-correct (successor of corridor.py r3).

Why r3 was not enough: the leaf hard cores (closed LEFs: OBS M1-M7, the leaf signal ceiling) leave NO track over a core,
so an ft bundle cannot "ride M6/M7" over one; in the adopt178 / faultfeed plan the cores sit under the N/S ft windows
and whole bundles squeeze through the 35-um W / S edge strip (PROTO G2: 30k-400k overflow, hot gcells at x<100 / y<100).

Method (industry practice, corridors FIRST):
  1. demand: every ft slot end is a window on a face; straight slots (opposite faces, overlapping windows) are one
     interval; windows that touch are merged into a cluster.  A cluster of B bits needs B / DV um of FULL-LENGTH free
     columns (N/S windows; DV = 16 b/um = M3+M5+M7 tracks x 0.5 G2 adjust x 0.5 utilisation) or B / DH um of
     full-width free rows (E/W windows; DH = 11 b/um = M2+M4+M6) inside the cluster's span.  Free = no core + FT_HALO.
  2. cores are placed as THREE rigid groups (internal geometry identical in every type -> intra-group station depths
     uniform): A = 4x4 lane block + vn_a/vn_b + vq + stores (tree in the lane streets), C = vs + vsw + rxsf + rxsb,
     D = ve_s + ve_m.  Inter-group links (vq/stores <-> vs, ve <-> vs) take ONE fixed station depth (XDEPTH = 1) in
     every type: only offsets whose every inter-group bundle fits 1 station (both hops <= 405 incl. pin spreads) count.
  3. search: A on a 17.28 grid scored by its own corridor shortfall, beam; then C, then D; hard objective = total
     corridor shortfall (um), then the bus term (vs / vq near the bus face); the G0C face rule (0 faces away) + legality
     on the final candidates.  The internal stations of the result are rebuilt by corridor.build (tree + inter-group).
usage: leafcorr4.py PLAN --out PLAN --report JSON [--types t6,t8] [--jobs N]"""
import argparse
import copy
import os
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import corridor as CR  # noqa: E402

TP, V = CR.TP, CR.V
CR.GROUPS.clear()
CR.GROUPS.update({
    "A": [CR.LN % i for i in range(16)] + ["u_lf.u_vn.u_a", "u_lf.u_vn.u_b", "u_lf.u_vq", "u_lf.u_vp.u_b0",
                                           "u_lf.u_vp.u_b1"],
    "C": ["u_lf.u_vs", "u_lf.u_vsw", "u_lf.u_rxsf", "u_lf.u_rxsb"],
    "D": ["u_lf.u_ve.u_s", "u_lf.u_ve.u_m"],
})
if os.environ.get("LEAF4_GROUPS", "3") == "2":     # r3 grouping: ve rides with vs (C), no D
    CR.GROUPS["C"] += CR.GROUPS.pop("D")
CR.GOF.clear()
CR.GOF.update({i: g for g, l in CR.GROUPS.items() for i in l})
DV, DH = 16.0, 11.0
HALO = V.FT_HALO
STEP = 2 * V.G
DC_MAX = float(os.environ.get("LEAF4_DC", "480"))   # ve <-> vs centre distance (no template entry: adjacent there)
CR.LINK_SLACK = float(os.environ.get("LEAF4_SLACK", "150"))   # one_site pushes the station out of the halos


def demand(T):
    """[(kind 'V'|'H', lo, hi, bits)] merged clusters"""
    ends = []
    for s in T.get("ft_slots", []):
        a = ("V" if s["in_face"] in "NS" else "H", *s["in_window_um"])
        b = ("V" if s["out_face"] in "NS" else "H", *s["out_window_um"])
        if a[0] == b[0] and a[1] <= b[2] and b[1] <= a[2]:
            ends.append((a[0], min(a[1], b[1]), max(a[2], b[2]), s["width"]))
        else:
            ends += [(a[0], a[1], a[2], s["width"]), (b[0], b[1], b[2], s["width"])]
    out = []
    for k in ("V", "H"):
        iv = sorted(e[1:] for e in ends if e[0] == k)
        cl = []
        for lo, hi, w in iv:
            if cl and lo <= cl[-1][1] + 2:
                cl[-1][1] = max(cl[-1][1], hi)
                cl[-1][2] += w
            else:
                cl.append([lo, hi, w])
        out += [(k, lo, hi, w) for lo, hi, w in cl]
    return out


class Corr:
    def __init__(self, T):
        self.W, self.H = T["outline_um"]
        self.dem = demand(T)
        self.nx, self.ny = int(self.W) + 1, int(self.H) + 1

    def occ(self, boxes):
        ox = np.zeros(self.nx, bool)
        oy = np.zeros(self.ny, bool)
        for x0, y0, x1, y1 in boxes:
            ox[max(0, int(x0 - HALO)):min(self.nx, int(x1 + HALO) + 1)] = True
            oy[max(0, int(y0 - HALO)):min(self.ny, int(y1 + HALO) + 1)] = True
        return ox, oy

    def short(self, ox, oy):
        s = 0.0
        for k, lo, hi, w in self.dem:
            o = ox if k == "V" else oy
            free = float((~o[int(lo):int(hi) + 1]).sum())
            s += max(0.0, w / (DV if k == "V" else DH) - free)
        return s

    def rows(self, ox, oy):
        r = []
        for k, lo, hi, w in self.dem:
            o = ox if k == "V" else oy
            free = float((~o[int(lo):int(hi) + 1]).sum())
            r.append(dict(k=k, span=[round(lo, 1), round(hi, 1)], bits=w, need_um=round(w / (DV if k == "V" else DH), 1),
                          free_um=free))
        return r


def faces(T, pl, rel, sz):
    pt = {i: (pl[g][0] + rel[g][i][0], pl[g][1] + rel[g][i][1]) for g in pl for i in CR.GROUPS[g]}
    o, _ = TP.place_type(T, pt, sz, None, 0.0, 0.0)
    cc = V.CORE_CONNS["leaf"]
    save = {h: {k: cc[h].pop(k) for k in ("rb_v", "rb_d", "n_go", "n_pre") if k in cc[h]}
            for h in ("u_lf.u_vn.u_a", "u_lf.u_vn.u_b")}
    try:
        return V.core_faces_away("leaf", o, T["outline_um"][0], T["outline_um"][1], T["buses"]), TP.legal(
            o, T["outline_um"][0], T["outline_um"][1])
    finally:
        for h, d in save.items():
            cc[h].update(d)


def search(T, rel, sz, gbox, lt, ctx, org, beamA=300, beamC=600, final=4000):
    W, H = T["outline_um"]
    cor = Corr(T)
    _, sbus, buses = CR.nframe_slots(T)
    # the search runs in the N-bus frame like r2/r3 (S-bus types y-mirrored): mirror the demand of S-bus types
    if sbus:
        cor.dem = [(k, (H - hi if k == "H" else lo), (H - lo if k == "H" else hi), w) for k, lo, hi, w in cor.dem]
    E = V.HC_EDGE_UM + 0.2
    bw = [b for b in buses if b["face"] == "N"]
    bx = np.mean([sum(b["window_um"]) / 2 for b in bw]) if bw else W / 2

    def pos(g):
        xs = np.arange(E, W - E - gbox[g][0] + 1e-6, STEP)
        ys = np.arange(E, H - E - gbox[g][1] + 1e-6, STEP)
        return [(round(float(x), 4), round(float(y), 4)) for x in xs for y in ys]

    def bxs(g, xy):
        return CR.gboxes(g, xy, rel, sz)

    def lok(pl):
        for ga, fa, gb, fb, spr, _ in lt:
            if ga in pl and gb in pl:
                L = abs(pl[ga][0] + fa[0] - pl[gb][0] - fb[0]) + abs(pl[ga][1] + fa[1] - pl[gb][1] - fb[1])
                if L + spr > (CR.XDEPTH + 1) * CR.REACH - CR.LINK_SLACK:
                    return False
        return True

    def busterm(pl):
        c = CR.centre("C", "u_lf.u_vs", pl["C"], rel, sz)
        t = 1265 * (abs(c[0] - bx) + (H - c[1]))
        c = CR.centre("A", "u_lf.u_vq", pl["A"], rel, sz)
        return t + 668 * (abs(c[0] - bx) + (H - c[1]))

    occ = {}

    def go(g, xy):
        k = (g, xy)
        if k not in occ:
            occ[k] = cor.occ(bxs(g, xy))
        return occ[k]
    PA = pos("A")
    sa = sorted(((cor.short(*go("A", a)), a) for a in PA), key=lambda t: t[0])[:beamA]
    if "D" not in CR.GROUPS:          # r3 grouping: C within +-8 x / +-16 y lattice steps of its template offset
        d0 = (org["C"][0] - org["A"][0], org["C"][1] - org["A"][1])
        vnx = rel["A"]["u_lf.u_vn.u_a"][0]
        cand = []
        for a in PA:
            oxa, oya = go("A", a)
            for i in range(-8, 9):
                for j in range(-16, 17):
                    c = (round(a[0] + d0[0] + i * STEP, 4), round(a[1] + d0[1] + j * STEP, 4))
                    if c[0] < a[0] + vnx or not (E <= c[0] and c[0] + gbox["C"][0] <= W - E and E <= c[1]
                                                 and c[1] + gbox["C"][1] <= H - E):
                        continue
                    pl = {"A": a, "C": c}
                    if not lok(pl) or not CR.sep_ok(bxs("A", a), bxs("C", c)):
                        continue
                    ox, oy = go("C", c)
                    cand.append((cor.short(oxa | ox, oya | oy), busterm(pl), pl))
        sa = []
    PC, PD = pos("C"), (pos("D") if "D" in CR.GROUPS else [])
    candC = []
    for s0, a in sa if "D" in CR.GROUPS else []:
        oxa, oya = go("A", a)
        for c in PC:
            pl = {"A": a, "C": c}
            if not lok(pl) or not CR.sep_ok(bxs("A", a), bxs("C", c)):
                continue
            ox, oy = go("C", c)
            candC.append((cor.short(oxa | ox, oya | oy), pl))
    candC.sort(key=lambda t: t[0])
    if "D" in CR.GROUPS:
        cand = []
    for s1, pl in ([] if "D" not in CR.GROUPS else candC[:beamC]):
        oxa, oya = go("A", pl["A"])
        oxc, oyc = go("C", pl["C"])
        for d in PD:
            p2 = dict(pl, D=d)
            if not lok(p2) or not CR.sep_ok(bxs("A", pl["A"]), bxs("D", d)) or not CR.sep_ok(bxs("C", pl["C"]),
                                                                                                bxs("D", d)):
                continue
            cv = CR.centre("C", "u_lf.u_vs", pl["C"], rel, sz)
            if any(abs(cv[0] - q[0]) + abs(cv[1] - q[1]) > DC_MAX
                   for q in (CR.centre("D", i, d, rel, sz) for i in CR.GROUPS["D"])):
                continue
            ox, oy = go("D", d)
            cand.append((cor.short(oxa | oxc | ox, oya | oyc | oy), busterm(p2), p2))
    cand.sort(key=lambda t: (round(t[0], 0), t[1]))
    hist = {}
    for sh, bt, pl in cand[:final]:
        f_, lg = faces(T, pl, rel, sz)
        hist[f_] = hist.get(f_, 0) + 1
        if f_ == 0 and lg:
            chk = CR.build(copy.deepcopy(T), dict(pl=pl), *ctx)
            if chk["xgroup_bad"] or chk["faces_away"] or not chk["legal"]:
                hist["xgroup_bad"] = hist.get("xgroup_bad", 0) + 1
                continue
            oxs = [go(g, pl[g]) for g in pl]
            ox = np.logical_or.reduce([o[0] for o in oxs])
            oy = np.logical_or.reduce([o[1] for o in oxs])
            return dict(pl=pl, short_um=round(sh, 1), score=round(bt, 1), sbus=sbus, ncand=len(cand), faces_hist=hist,
                        corridors=cor.rows(ox, oy), cost=0.0, viol_paths=0)
    print(T.get("module"), "no face-clean candidate; hist", hist, "ncand", len(cand), "best short",
          cand[0][0] if cand else None, flush=True)
    return None


def work(args):
    tn, T, T0 = args
    p, sz, lane_off, rel, gbox, org = CR.template_groups()
    lt = CR.link_table(T0, p, sz, rel, org)
    r = search(T, rel, sz, gbox, lt, (p, sz, lane_off, rel, org), org)
    if r is None:
        return tn, None, None
    info = CR.build(T, r, p, sz, lane_off, rel, org)
    info.update({k: r[k] for k in ("short_um", "score", "ncand", "corridors", "faces_hist")})
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
    T0 = P["partition_types"]["ot_s81sl_leaf__t1"]
    todo = [(tn, T, T0) for tn, T in P["partition_types"].items()
            if tn.startswith("ot_s81sl_leaf__t") and (not sel or tn.split("__")[1] in sel)]
    p, sz, lane_off, rel, gbox, org = CR.template_groups()
    rep = dict(groups={g: dict(insts=l, bbox=[round(v, 2) for v in gbox[g]]) for g, l in CR.GROUPS.items()},
               xdepth=CR.XDEPTH, dv=DV, dh=DH, types={})
    with Pool(a.jobs) as pool:
        for tn, info, upd in pool.imap_unordered(work, todo):
            rep["types"][tn] = info
            if upd:
                P["partition_types"][tn].update(upd)
            print(tn, None if info is None else {k: v for k, v in info.items() if k not in ("depth", "corridors")},
                  flush=True)
    cls = {}
    for tn, info in rep["types"].items():
        for k, d in (info or {}).get("depth", {}).items():
            if k.startswith("core:"):
                cls.setdefault(k, set()).add(d)
    rep["nonuniform"] = {k: sorted(v) for k, v in cls.items() if len(v) > 1}
    print("nonuniform classes:", rep["nonuniform"])
    if a.out:
        Path(a.out).write_text(json.dumps(P, indent=0) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
