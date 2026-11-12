#!/usr/bin/env python3
"""Per-type feasibility bound, independent of placement (COORD 11-12, owner: "can some types NEVER fit?").

    type_bound.py PLAN --die NAME [--repo .] [--ref-dirs ...] [--types ..|--match RE] --out DIR

For every partition type:
 (a) cuts: every vertical / horizontal line through the type (scanned on a 2.16-um pitch, plus the centre of every
     core-to-core channel).  Demand = the nets that MUST cross the line (route_supply's own net list: core-to-core,
     core-to-face, ft hops, station links; a net crosses when its pin bbox spans the line).  Supply = tracks across
     the line on M2..M9 in the crossing direction (route_supply's measured effective pitch x (1 - GRT derate); M8/M9
     0.080 um, derate 0.35), with the layers at or below the core ceiling (M5) blocked where the line runs over a
     hard core.  Growth: the line gets longer by the type's MAX growth on the other axis = the die's reticle headroom
     divided by how often the type stacks along that die axis (street_rule.die_growth push model, this type alone
     grown: an optimistic bound -- the headroom is shared by every type).
 (b) faces: pins on a fixed face (die edge for every instance, or a PHY / pad type) vs face length x pin tracks
     per um on the layers that reach that face (N/S: M3/M5/M7/M9, E/W: M2/M4/M6/M8).  PHY faces at their current
     length, die-edge faces at max growth along the edge.
 (c) cells vs the 400k OpenROAD cap (measured synth of the type's top when known, else the plan estimate when the
     type has no hard cores; flat counts incl. hard cores are reported, not judged).
Classes: NEEDS-SPLIT (> 400k) / FITS (every cut and fixed face fits at the current outline) / FITS-WITH-GROWTH
(fits within the max growth) / NEEDS-BANDWIDTH (does not fit even at max growth; worst cut dominated by ft / face
pass-through, or a fixed face over capacity: serialise or reroute) / NEEDS-REPARTITION (worst cut dominated by the
type's own core-to-core / core-to-face nets: move logic between types or dies).
Bound semantics: demand counts only wires that must cross (no detour, no background cell wiring, no GRT halving),
supply counts every track: a type that fails here cannot fit by any placement keeping the core order.
"""
import argparse
import collections
import contextlib
import io
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import route_supply as RS  # noqa: E402
import street_rule as SR  # noqa: E402

CELL_CAP = 400_000
LAY = dict(RS.PITCH)
LAY.update(M8=0.080, M9=0.080)
DER = dict(RS.DERATE)
DER.update(M8=0.35, M9=0.35)
DIRN = dict(RS.DIRN)
DIRN.update(M8="H", M9="V")
ORDER = ["M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]
STEP = 2.16


def per_um(direction, above=None, top="M9"):
    """tracks per um across a line, wires running in `direction`, layers above `above` only (None = all)."""
    lo = ORDER.index(above) + 1 if above else 0
    hi = ORDER.index(top) + 1
    return sum((1 - DER[L]) / LAY[L] for L in ORDER[lo:hi] if DIRN[L] == direction)


FACE_MAP = {
    "R0": dict(N="N", S="S", E="E", W="W"), "MX": dict(N="S", S="N", E="E", W="W"),
    "MY": dict(N="N", S="S", E="W", W="E"), "R180": dict(N="S", S="N", E="W", W="E"),
    "R90": dict(N="W", W="S", S="E", E="N"), "R270": dict(N="E", E="S", S="W", W="N"),
    "MXR90": dict(N="E", S="W", E="N", W="S"), "MYR90": dict(N="W", S="E", E="S", W="N"),
}


def fixed_faces(P, tn, t):
    """faces fixed by the die edge (every instance) or by a PHY / pad binding (all faces)."""
    if t.get("pads") or any(k.startswith("phy_") for k in t) or t.get("rck_band"):
        return {f: "phy" for f in "NSEW"}
    Wd, Hd = map(float, P["die"]["outline_um"])
    w, h = map(float, t["outline_um"])
    inst = [p for p in P.get("partitions") or [] if p.get("type") == tn]
    if not inst:
        return {}
    hit = None
    for p in inst:
        o = p.get("orient") or "R0"
        ww, hh = (h, w) if o in ("R90", "R270", "MXR90", "MYR90") else (w, h)
        x, y = map(float, p["origin_um"])
        edge = set()
        if x <= 1.0:
            edge.add("W")
        if y <= 1.0:
            edge.add("S")
        if x + ww >= Wd - 1.0:
            edge.add("E")
        if y + hh >= Hd - 1.0:
            edge.add("N")
        fm = FACE_MAP.get(o, FACE_MAP["R0"])
        tf = {f for f in "NSEW" if fm[f] in edge}
        hit = tf if hit is None else hit & tf
    return {f: "die_edge" for f in sorted(hit or ())}


def face_pins(t):
    c = collections.Counter()
    for b in t.get("buses") or []:
        if b.get("face") in ("N", "S", "E", "W"):
            c[b["face"]] += int(b.get("width") or 1)
    for f in t.get("ft_slots") or []:
        for k in ("in_face", "out_face"):
            if f.get(k) in ("N", "S", "E", "W"):
                c[f[k]] += int(f.get("width") or 1)
    return c


def growth_room(P, tn, t, delta=8.64):
    """max growth (um) of this type's W and H with every other type fixed: die reticle headroom / push factor."""
    Wd, Hd = map(float, P["die"]["outline_um"])
    hi = sorted(SR.RETICLE_UM)
    capx, capy = (hi[1], hi[0]) if Wd >= Hd else (hi[0], hi[1])
    hx, hy = max(0.0, capx - Wd), max(0.0, capy - Hd)
    w, h = map(float, t["outline_um"])
    out = []
    for g in ((w + delta, h), (w, h + delta)):
        d = SR.die_growth(P, {tn: g})
        kx, ky = d["dW"] / delta, d["dH"] / delta
        room = min(hx / kx if kx > 1e-9 else float("inf"), hy / ky if ky > 1e-9 else float("inf"))
        out.append(room)
    return out[0], out[1], [hx, hy]


def profile(nets, cats, L, along_lo, along_hi, rects, lo_i, hi_i):
    """demand per cut position on [0, L] (nets spanning the position), split by category; core-covered length."""
    xs = np.arange(STEP / 2, L, STEP)
    if len(xs) == 0:
        return xs, {}, np.zeros(0)
    dem = {c: np.zeros(len(xs) + 1) for c in cats}
    for cat, a, b, n in nets:
        if b - a < 1e-6:
            continue
        i0 = np.searchsorted(xs, a, side="right")
        i1 = np.searchsorted(xs, b, side="left")
        if i1 > i0:
            dem[cat][i0] += n
            dem[cat][i1] -= n
    dem = {c: np.cumsum(v)[:-1] for c, v in dem.items()}
    cov = np.zeros(len(xs) + 1)
    for r in rects:
        a, b = r[lo_i], r[hi_i]
        i0 = np.searchsorted(xs, a, side="right")
        i1 = np.searchsorted(xs, b, side="left")
        if i1 > i0:
            cov[i0] += r[along_hi] - r[along_lo]
            cov[i1] -= r[along_hi] - r[along_lo]
    return xs, dem, np.cumsum(cov)[:-1]


def channel_centres(rects, ax):
    """centres (on axis ax) of the gaps between cores that face each other on ax (overlap on the other axis)."""
    o = 1 - ax
    out = set()
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            if min(a[2 + o], b[2 + o]) - max(a[o], b[o]) <= 1e-3:
                continue
            for p, q in ((a, b), (b, a)):
                g0, g1 = p[2 + ax], q[ax]
                if g1 - g0 >= -1e-6:
                    out.add(round((g0 + g1) / 2, 3))
    return sorted(out)


def cut_check(rec, W, H, rects, room, top="M9", ceiling="M5"):
    """worst cut per direction. Vertical cut (line x = c) is crossed by H wires; its length H grows by room[1]."""
    res = {}
    cats = sorted({r[0] for r in rec} | {"core"})
    for name, ax, L, Lperp, grow, wdir in (("vcut", 0, W, H, room[1], "H"), ("hcut", 1, H, W, room[0], "V")):
        nets = [(r[0], r[2], r[3], r[6]) if ax == 0 else (r[0], r[4], r[5], r[6]) for r in rec]
        xs, dem, cov = profile(nets, cats, L, 1 - ax, 3 - ax, rects, ax, ax + 2)
        if len(xs) == 0:
            continue
        tot = sum(dem.values())
        s_all, s_above = per_um(wdir, top=top), per_um(wdir, above=ceiling, top=top)
        cov = np.minimum(cov, Lperp)
        sup0 = (Lperp - cov) * s_all + cov * s_above
        need = np.maximum(0.0, (tot - sup0) / s_all)          # extra perpendicular length to fit this cut
        ratio = tot / np.maximum(sup0, 1e-9)
        keep = (xs > 2.0) & (xs < L - 2.0)
        if not keep.any():
            keep = np.ones(len(xs), bool)
        i = int(np.argmax(np.where(keep, ratio, -1)))
        j = int(np.argmax(np.where(keep, need, -1)))
        ch = channel_centres(rects, ax)
        chw = None
        if ch:
            ci = [int(np.clip(np.searchsorted(xs, c), 0, len(xs) - 1)) for c in ch]
            k = max(ci, key=lambda q: ratio[q])
            chw = dict(at_um=round(float(xs[k]), 2), demand=int(tot[k]), supply=int(sup0[k]), ratio=round(float(ratio[k]), 3),
                       n_channels=len(ch))
        mix = {c: int(v[j]) for c, v in dem.items() if v[j]}
        res[name] = dict(at_um=round(float(xs[i]), 2), demand=int(tot[i]), supply=int(sup0[i]), ratio=round(float(ratio[i]), 3),
                         need_growth_um=round(float(need[j]), 1), need_at_um=round(float(xs[j]), 2), room_um=round(grow, 1),
                         mix_at_need=mix, worst_channel=chw)
    return res


def classify(cells, cuts, faces):
    if cells and cells > CELL_CAP:
        return "NEEDS-SPLIT", "cells %d > %d" % (cells, CELL_CAP)
    bad_face = [f for f, v in faces.items() if v["fixed"] and v["ratio_at_limit"] > 1.0]
    if bad_face:
        return "NEEDS-BANDWIDTH", "fixed face %s pins over capacity (%s)" % (
            ",".join(bad_face), ", ".join("%s %d/%d" % (f, faces[f]["pins"], faces[f]["cap_at_limit"]) for f in bad_face))
    cur = all(c["ratio"] <= 1.0 for c in cuts.values()) and all(
        v["ratio_now"] <= 1.0 for v in faces.values() if v["fixed"])
    if cur:
        return "FITS", ""
    over = {k: c for k, c in cuts.items() if c["need_growth_um"] > c["room_um"] + 1e-6}
    if not over:
        return "FITS-WITH-GROWTH", "; ".join("%s needs +%.0f um (room %.0f)" % (k, c["need_growth_um"], c["room_um"])
                                             for k, c in cuts.items() if c["need_growth_um"] > 0)
    k, c = max(over.items(), key=lambda kv: kv[1]["need_growth_um"] - kv[1]["room_um"])
    mix = c["mix_at_need"]
    tot = max(1, sum(mix.values()))
    ft = mix.get("ft", 0)
    why = "%s at %.0f um needs +%.0f um, room %.0f; crossing mix %s" % (
        k, c["need_at_um"], c["need_growth_um"], c["room_um"], ", ".join("%s %d" % kv for kv in sorted(mix.items())))
    return ("NEEDS-BANDWIDTH" if ft / tot >= 0.5 else "NEEDS-REPARTITION"), why


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--die", required=True)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--ref-dirs", nargs="*", default=[])
    ap.add_argument("--types")
    ap.add_argument("--match")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    REC, CB = {}, {}
    oa, od = RS.analyze_type, RS.add_density

    def wa(name, t, die_dir, repo, conns, cfg):
        r = oa(name, t, die_dir, repo, conns, dict(cfg, record_nets=True))
        if r is not None:
            REC[name] = r.get("_rec") or []
        return r

    def wd(r, t, cb):
        CB[r["type"]] = cb
        return od(r, t, cb)
    RS.analyze_type, RS.add_density = wa, wd
    argv2 = [a.plan, "--die", a.die, "--repo", a.repo, "--out", str(out / "rs"), "--grt-halving", "edge_outline"]
    if a.ref_dirs:
        argv2 += ["--ref-dirs"] + a.ref_dirs
    if a.types:
        argv2 += ["--types", a.types]
    if a.match:
        argv2 += ["--match", a.match]
    with contextlib.redirect_stdout(io.StringIO()):
        RS.main(argv2)
    P, sha = SR.load_plan(Path(a.plan) if Path(a.plan).is_absolute() else Path(a.repo) / a.plan)
    T = P["partition_types"]
    rows = []
    for tn in sorted(REC):
        t = T[tn]
        W, H = map(float, t["outline_um"])
        rects = SR._core_rects(t)
        room_w, room_h, head = growth_room(P, tn, t)
        cuts = cut_check(REC[tn], W, H, rects, (room_w, room_h))
        cuts7 = cut_check(REC[tn], W, H, rects, (room_w, room_h), top="M7")
        fx = fixed_faces(P, tn, t)
        fp = face_pins(t)
        faces = {}
        for f in "NSEW":
            if not fp.get(f):
                continue
            L = W if f in ("N", "S") else H
            room = room_w if f in ("N", "S") else room_h
            cap_um = per_um("V" if f in ("N", "S") else "H")
            lim = L if fx.get(f) == "phy" else L + room
            faces[f] = dict(pins=fp[f], len_um=round(L, 1), fixed=fx.get(f), cap_now=int(L * cap_um),
                            cap_at_limit=int(min(lim, 1e7) * cap_um), ratio_now=round(fp[f] / (L * cap_um), 3),
                            ratio_at_limit=round(fp[f] / (min(lim, 1e7) * cap_um), 3))
        cb = CB.get(tn) or (None, None)
        cells, basis = cb
        if cells is None and not t.get("hard_cores") and t.get("cells"):
            cells, basis = int(t["cells"]), "plan cells"
        cls, why = classify(cells, cuts, faces)
        cls7, _ = classify(cells, cuts7, faces)
        rows.append(dict(type=tn, cls=cls, why=why, cls_m2_m7=cls7, outline_um=[W, H], cores=len(rects),
                         room_um=[round(min(room_w, 1e7), 1), round(min(room_h, 1e7), 1)], die_headroom_um=head,
                         cells=cells, cells_basis=basis, cells_flat_plan=t.get("cells"), cuts=cuts,
                         cuts_m2_m7={k: dict(ratio=v["ratio"], need_growth_um=v["need_growth_um"]) for k, v in cuts7.items()},
                         faces=faces, nets=len(REC[tn])))
    cnt = collections.Counter(r["cls"] for r in rows)
    cnt7 = collections.Counter(r["cls_m2_m7"] for r in rows)
    js = dict(schema="opentallas.type_bound.v1", die=a.die, plan=a.plan, plan_sha256=sha, counts=dict(cnt),
              counts_m2_m7=dict(cnt7), cell_cap=CELL_CAP, rows=rows)
    (out / ("type_bound_%s.json" % a.die)).write_text(json.dumps(js, indent=1))
    with open(out / ("type_bound_%s.tsv" % a.die), "w") as f:
        f.write("type\tclass\tclass_M2-M7\tcores\tW\tH\troom_W\troom_H\tvcut_ratio\tvcut_need_um\thcut_ratio\thcut_need_um\t"
                "cells\twhy\n")
        for r in sorted(rows, key=lambda r: (r["cls"], r["type"])):
            v, h = r["cuts"].get("vcut", {}), r["cuts"].get("hcut", {})
            f.write("\t".join(str(x) for x in (r["type"], r["cls"], r["cls_m2_m7"], r["cores"], r["outline_um"][0],
                                                r["outline_um"][1], r["room_um"][0], r["room_um"][1], v.get("ratio"),
                                                v.get("need_growth_um"), h.get("ratio"), h.get("need_growth_um"),
                                                r["cells"], re.sub(r"\s+", " ", r["why"]))) + "\n")
    print(a.die, "types", len(rows), dict(cnt), "| M2-M7 only:", dict(cnt7))
    return 0


if __name__ == "__main__":
    sys.exit(main())
