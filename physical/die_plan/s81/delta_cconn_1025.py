#!/usr/bin/env python3
"""S81-PLAN2/CCONN 10-25 (COORD ruling 10-25 + S81-CORES RULINGS (3) 05:40): core re-placement delta for the hard-core
types whose connectivity comes from inputs/core_conns_derived.json (13 landed col_h* frames, gunit, bk_sel).

With derived core connectivity on (gen_plan_v4.derived_core_conns, now DEFAULT, driver -> sink pairs only), G0C
R3-INTERNAL needs every core <-> core and bus window <-> core bundle <= ft_station_max_um (405 um) or a FIRM
internal_stations[] entry.  This delta fixes the hops STRUCTURALLY by moving cores (no RTL / latency change):

  1. qbank_S growth (S81-CORES kit CTS DPL-0038, util 118 %): every dsfd_qbank_S hard core 60.48 x 17.28 ->
     60.48 x 25.92 um (+1 8.64 lattice row; pin faces / width kept; the N-face pins move up 8.64 um ->
     inputs/core_pins/dsfd_qbank_S.json is rewritten here, the LEF / views are S81-CORES's regen).  The core grows
     up when the row above is free, else down, else it is re-placed by step 2.
  2. for each violating bundle (and each overlap left by 1) move ONE of the two cores to the lattice site (8.64 um)
     with the least displacement where ALL of the moved core's driver/sink partners (cores and bus windows) sit
     <= REACH, it overlaps no core (HALO clearance), no FT station bit-site box and stays inside the outline.
     The core that moves is the one with fewer partners (ties: the smaller).
Types / bundles the mover cannot close are reported (unresolved) and left to FIRM internal stations.

    python3 physical/die_plan/s81/delta_cconn_1025.py PLAN [OUT] [--report REP.json]
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(HERE), str(REPO), str(REPO / "tools" / "die_plan")]

G = 8.64
REACH = 405.0 - 9.0          # placement target: a lattice step inside the 405-um R3 limit
HALO = 4.32                  # clearance between hard cores (half a lattice step)
FT_KEEP = 4.32               # clearance around FT station bit-site boxes
QBS = ("dsfd_qbank_S", 25.92)


def _box(h):
    x, y = h["origin_um"]
    w, hh = h["outline_um"]
    if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, hh = hh, w
    return [x, y, x + w, y + hh]


def _d(a, b):
    return max(a[0] - b[2], b[0] - a[2], 0) + max(a[1] - b[3], b[1] - a[3], 0)


def _dp(p, b):
    return max(b[0] - p[0], 0, p[0] - b[2]) + max(b[1] - p[1], 0, p[1] - b[3])


def _ov(a, b, c):
    return a[0] < b[2] + c and b[0] < a[2] + c and a[1] < b[3] + c and b[1] < a[3] + c


def _ft_boxes(t):
    out = []
    for s in t.get("ft_slots", []):
        bs = s.get("bit_sites_um")
        if isinstance(bs, str):
            bs = json.loads(bs)
        for st in bs or []:
            pts = st if st and isinstance(st[0], list) else [st]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out.append([min(xs) - FT_KEEP, min(ys) - FT_KEEP, max(xs) + FT_KEEP, max(ys) + FT_KEEP])
        for r in s.get("regs_um", []):
            out.append([r[0] - FT_KEEP, r[1] - FT_KEEP, r[0] + FT_KEEP, r[1] + FT_KEEP])
    return out


def _partners(conns, bt):
    """{inst: {('core', other) | ('bus', name, (x, y))}} both directions."""
    pr = {}
    for ci, ports in conns.items():
        for tgs in ports.values():
            for tg in tgs:
                k, _, n = tg.partition(":")
                if k == "core":
                    pr.setdefault(ci, set()).add(("core", n))
                    pr.setdefault(n, set()).add(("core", ci))
                elif k == "bus" and n in bt:
                    pr.setdefault(ci, set()).add(("bus", n, tuple(bt[n][1])))
    return pr


def _worst(ci, b, boxes, pr):
    w = 0.0
    for p in pr.get(ci, ()):
        w = max(w, _d(b, boxes[p[1]]) if p[0] == "core" else _dp(p[2], b))
    return w


def _violations(boxes, pr, lim):
    v = []
    for ci in sorted(pr):
        for p in sorted(pr[ci], key=str):
            if p[0] == "core" and ci < p[1] and _d(boxes[ci], boxes[p[1]]) > lim:
                v.append((ci, p[1]))
            elif p[0] == "bus" and _dp(p[2], boxes[ci]) > lim:
                v.append((ci, None))
    return v


def _site(ci, boxes, W, H, ft, pr, edge):
    """least-displacement lattice site for ci with every partner <= REACH; None if there is none."""
    x0, y0, x1, y1 = boxes[ci]
    w, h = x1 - x0, y1 - y0
    others = [b for k, b in boxes.items() if k != ci]
    best = None
    nx, ny = int((W - w - edge) // G), int((H - h - edge) // G)
    lo = int(round(edge / G))
    for ix in range(lo, nx + 1):
        x = ix * G
        for iy in range(lo, ny + 1):
            y = iy * G
            cost = abs(x - x0) + abs(y - y0)
            if best is not None and cost >= best[0]:
                continue
            b = [x, y, x + w, y + h]
            if _worst(ci, b, boxes, pr) > REACH:
                continue
            if any(_ov(b, o, HALO) for o in others) or any(_ov(b, f, 0) for f in ft):
                continue
            best = (cost, b)
    return best


def _anneal(boxes, pr, W, H, ft, edge, seed=1, iters=60000):
    """small types (<= 12 cores, e.g. gunit / bk_sel): lattice simulated annealing of ALL core sites, cost = sum of
    partner excess over REACH + overlap; returns new boxes (or the input when it does not improve)."""
    import math
    import random
    rnd = random.Random(seed)
    ks = sorted(boxes)
    wh = {k: (boxes[k][2] - boxes[k][0], boxes[k][3] - boxes[k][1]) for k in ks}

    def cost(bx):
        c = 0.0
        for k in ks:
            for p in pr.get(k, ()):
                if p[0] == "core" and k < p[1]:
                    c += max(0.0, _d(bx[k], bx[p[1]]) - REACH)
                elif p[0] == "bus":
                    c += max(0.0, _dp(p[2], bx[k]) - REACH)
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                A, B = bx[a], bx[b]
                ox = min(A[2], B[2]) + HALO - max(A[0], B[0])
                oy = min(A[3], B[3]) + HALO - max(A[1], B[1])
                if ox > 0 and oy > 0:
                    c += 50.0 * min(ox, oy) + 1000.0
            if any(_ov(bx[a], f, 0) for f in ft):
                c += 1000.0
        return c
    cur = {k: list(v) for k, v in boxes.items()}
    cc = c0 = cost(cur)
    best, bc = {k: list(v) for k, v in cur.items()}, cc
    T0 = 400.0
    for it in range(iters):
        T = T0 * (1 - it / iters) + 1e-3
        k = rnd.choice(ks)
        w, h = wh[k]
        nb = dict(cur)
        if rnd.random() < 0.15:
            k2 = rnd.choice(ks)
            x, y = cur[k2][0], cur[k2][1]
            x2, y2 = cur[k][0], cur[k][1]
            w2, h2 = wh[k2]
            nb[k] = [x, y, x + w, y + h]
            nb[k2] = [x2, y2, x2 + w2, y2 + h2]
        else:
            step = max(G, T)
            x = cur[k][0] + rnd.gauss(0, step)
            y = cur[k][1] + rnd.gauss(0, step)
            x = min(max(edge, round(x / G) * G), math.floor((W - w - edge) / G) * G)
            y = min(max(edge, round(y / G) * G), math.floor((H - h - edge) / G) * G)
            nb[k] = [x, y, x + w, y + h]
        if any(b[0] < edge - 1e-6 or b[1] < edge - 1e-6 or b[2] > W - edge + 1e-6 or b[3] > H - edge + 1e-6
               for b in nb.values()):
            continue
        nc = cost(nb)
        if nc <= cc or rnd.random() < math.exp((cc - nc) / T):
            cur, cc = nb, nc
            if cc < bc:
                best, bc = {kk: list(v) for kk, v in cur.items()}, cc
                if bc == 0:
                    break
    return (best, bc, c0) if bc < c0 else (boxes, c0, c0)


def _orients(t, conns, bt, plan_dir):
    """core_faces (GEOM face rule): per core pick the orient among R0 / MX / MY / R180 (macro mirror, footprint kept)
    with the fewest ports whose pins face away from their partners; ties keep the current orient."""
    import re
    import check as C
    hcs = t["hard_cores"]
    cent = {}
    for hc in hcs:
        cw, ch = hc["outline_um"]
        dx, dy = hc.get("track_offset_um", [0.0, 0.0])
        cent[hc["inst"]] = (hc["origin_um"][0] + dx + cw / 2, hc["origin_um"][1] + dy + ch / 2)
    flips = {}
    for hc in hcs:
        ci = hc["inst"]
        ports = conns.get(ci)
        if not ports:
            continue
        try:
            pins = C.core_pins(hc, plan_dir)
        except (OSError, ValueError, KeyError):
            continue
        cw, ch = hc["outline_um"]
        cx, cy = cent[ci]
        base = {}
        for nm, _l, x, y in pins:
            base.setdefault(re.sub(r"\[\d+\]$", "", nm), []).append((x, y))

        def away(o):
            n = 0
            for lp, tgs in ports.items():
                if lp not in base:
                    continue
                dirs = []
                for tg in tgs:
                    k, _, nm = tg.partition(":")
                    pt = cent.get(nm) if k == "core" else (tuple(bt[nm][1]) if k == "bus" and nm in bt else None)
                    if pt:
                        d = ((pt[0] - cx) ** 2 + (pt[1] - cy) ** 2) ** .5
                        if d > 1e-6:
                            dirs.append(((pt[0] - cx) / d, (pt[1] - cy) / d))
                if not dirs:
                    continue
                cs = []
                for x, y in base[lp]:
                    f = C._core_face(o, x, y, cw, ch)
                    cs.append(max(C._NORMAL[f][0] * ux + C._NORMAL[f][1] * uy for ux, uy in dirs))
                if sum(cs) / len(cs) < C.FACE_AWAY_COS:
                    n += 1
            return n
        cur = hc.get("orient", "R0")
        sc = {o: away(o) for o in (cur, "R0", "MX", "MY", "R180")}
        best = min(sc, key=lambda o: (sc[o], o != cur))
        if best != cur and sc[best] < sc[cur]:
            hc["orient"] = best
            flips[ci] = dict(frm=cur, to=best, away=[sc[cur], sc[best]])
    return flips


def apply(raw):
    import gen_plan_v4 as GP
    import check as C
    import schema as S
    T = raw["partition_types"]
    GP.CORE_CONNS_OUT.clear()
    GP.derived_core_conns(T)
    P = S.Plan(raw, None)
    rep = dict(types={}, qbank_S=dict(grown_up=0, grown_down=0, replaced=0))
    for tn in sorted(GP.CORE_CONNS_OUT):
        t = T[tn]
        conns = GP.CORE_CONNS_OUT[tn]
        bt = C._bus_targets(P, tn)
        pr = _partners(conns, bt)
        W, H = t["outline_um"]
        hcs = {h["inst"]: h for h in t["hard_cores"]}
        boxes = {k: _box(h) for k, h in hcs.items()}
        edge = min(min(b[0], b[1], W - b[2], H - b[3]) for b in boxes.values())
        edge = max(0.0, min(edge, 2 * G))
        ft = _ft_boxes(t)
        moved, overlap = {}, set()
        # 1. qbank_S +1 lattice row
        for k, h in hcs.items():
            if h["module"] != QBS[0] or h["outline_um"][1] >= QBS[1] - 1e-6:
                continue
            dh = QBS[1] - h["outline_um"][1]
            b = boxes[k]
            up, dn = [b[0], b[1], b[2], b[3] + dh], [b[0], b[1] - dh, b[2], b[3]]
            ok = lambda nb: (nb[1] >= edge - 1e-6 and nb[3] <= H - edge + 1e-6 and
                             not any(_ov(nb, o, HALO) for kk, o in boxes.items() if kk != k) and
                             not any(_ov(nb, f, 0) for f in ft))
            if ok(up):
                boxes[k] = up
                rep["qbank_S"]["grown_up"] += 1
            elif ok(dn):
                boxes[k] = dn
                rep["qbank_S"]["grown_down"] += 1
            else:
                boxes[k] = up
                overlap.add(k)
                rep["qbank_S"]["replaced"] += 1
            h["outline_um"] = [h["outline_um"][0], QBS[1]]
        for k in sorted(overlap):
            s = _site(k, boxes, W, H, ft, pr, edge)
            if s:
                moved[k] = [round(v, 3) for v in boxes[k][:2]], s[1][:2]
                boxes[k] = s[1]
                overlap.discard(k)
        before = _violations(boxes, pr, 405.0)
        unresolved = []
        for it in range(200):
            v = _violations(boxes, pr, 405.0)
            v = [x for x in v if x not in unresolved]
            if not v:
                break
            a, b = v[0]
            cands = [a] if b is None else sorted([a, b], key=lambda c: (len(pr.get(c, ())),
                                                                         (boxes[c][2] - boxes[c][0]) *
                                                                         (boxes[c][3] - boxes[c][1])))
            done = False
            for c in cands:
                s = _site(c, boxes, W, H, ft, pr, edge)
                if s:
                    moved.setdefault(c, ([round(x, 3) for x in boxes[c][:2]], None))
                    moved[c] = (moved[c][0], s[1][:2])
                    boxes[c] = s[1]
                    done = True
                    break
            if not done:
                unresolved.append((a, b))
        annealed = None
        if unresolved and len(hcs) <= 12:
            bx0 = {k: list(v) for k, v in boxes.items()}
            nb, c1, c0 = min((_anneal(bx0, pr, W, H, ft, edge, seed=s) for s in range(1, 9)), key=lambda r: r[1])
            if c1 < c0:
                boxes = nb
                annealed = dict(excess_um_before=round(c0, 1), excess_um_after=round(c1, 1))
                for k in hcs:
                    if boxes[k][:2] != bx0[k][:2]:
                        moved.setdefault(k, ([round(x, 3) for x in bx0[k][:2]], None))
                        moved[k] = (moved[k][0], boxes[k][:2])
                unresolved = [x for x in _violations(boxes, pr, 405.0)]
        for k, h in hcs.items():
            h["origin_um"] = [round(boxes[k][0], 3), round(boxes[k][1], 3)]
        flips = _orients(t, conns, bt, str(HERE))
        rep["types"][tn] = dict(orient_flips=flips,
            
            bundle_pairs_before=len(before), moved={k: dict(frm=v[0], to=[round(x, 3) for x in v[1]])
                                                    for k, v in moved.items() if v[1]},
            unresolved=[dict(core=a, partner=b, um=round(_d(boxes[a], boxes[b]) if b else
                                                         _worst(a, boxes[a], boxes, pr), 1)) for a, b in unresolved],
            overlap_left=sorted(overlap), annealed=annealed)
    return rep


def qbank_s_pins(path):
    """N-face pins of dsfd_qbank_S up by the +8.64 row (y > half height); S / W pins unchanged."""
    d = json.load(open(path))
    if d.get("outline_um") == [60.48, QBS[1]] or any(p["y"] > 17.28 for p in d["pins"]):
        return False
    for p in d["pins"]:
        if p["y"] > 8.64:
            p["y"] = round(p["y"] + QBS[1] - 17.28, 4)
    d["source"] = d.get("source", "") + " | S81-PLAN2/CCONN 10-25: +8.64 um row (60.48 x 25.92), N pins +8.64"
    open(path, "w").write(json.dumps(d, indent=1) + "\n")
    return True


def main():
    pf = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else pf
    raw = json.load(open(pf))
    pins_rw = qbank_s_pins(HERE / "inputs" / "core_pins" / "dsfd_qbank_S.json") if "--pins" in sys.argv else None
    rep = apply(raw)
    rep["qbank_S_pins_rewritten"] = pins_rw
    try:
        import pdump
        txt = pdump.dumps(raw)
    except ImportError:
        txt = json.dumps(raw, indent=1) + "\n"
    open(out, "w").write(txt)
    if "--report" in sys.argv:
        open(sys.argv[sys.argv.index("--report") + 1], "w").write(json.dumps(rep, indent=1) + "\n")
    for tn, r in rep["types"].items():
        print(tn, "flips", len(r["orient_flips"]), "pairs>405 before", r["bundle_pairs_before"], "moved", len(r["moved"]), "unresolved",
              len(r["unresolved"]), "overlap_left", r["overlap_left"])
    print("qbank_S", rep["qbank_S"])


if __name__ == "__main__":
    main()
