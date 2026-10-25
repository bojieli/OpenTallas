#!/usr/bin/env python3
"""S81/LEAFPLAN 10-24: per-type leaf core arrangement search (simulated annealing) on the generator's own ranking key.

The generator (gen_plan_v4.nonframe_hard_cores) ranks every leaf candidate by
  (core ports facing away (G0C face rule), bus window -> core box excess over FT_STATION_MAX (750),
   added cycles = ft stations over the no-core model at the 405-um kit reach + internal-station cycles per core pair).
This tool searches one type's arrangement of the 25 leaf cores (16 hcpl lanes, 2 store SRAMs, vn, vq, vs, vsw, ve, rxsf,
rxsb) and the pin VIEW of vn / vq / vs (R0 or the x-mirrored variant "xm", cores/leaf/xmirror.py) on exactly that key
(G.core_faces_away, G.core_internal_stations, G.ft_stations_macro), plus shaping terms (bundle length per core pair,
lane cohesion around vn's hq/hw ports) so the annealer has a gradient between station counts.

Inputs: the per-type dump the generator writes with S81_HC_DUMP=<file> (outline, buses, ft slots before cores).
Output: <out>.json = {"type", "place": {inst: [x, y]}, "views": {inst: "xm"}, "key", "detail"} in the DESIGN frame (bus
face N; the generator y-mirrors S-bus types), the format of cores/leaf/alt_place.json candidates.
usage (repo root): python3 physical/die_plan/s81/cores/leaf/search.py DUMP TYPE SEED ITERS OUT [INIT.json|-|tmpl:<n>]"""
import json, math, os, random, sys
sys.path.insert(0, "physical/die_plan/s81")
sys.path.insert(0, "tools/die_plan")
import gen_plan_v4 as G   # noqa: E402

SPEC = G.NONFRAME_HC["leaf"]
K = "leaf"
XV = SPEC["xmirror_views"]
VIEWABLE = sorted(SPEC["views"][XV])
CORES = {c["inst"]: c for c in SPEC["cores"]}
SIZE = {i: G._lef_size(c["lef"]) for i, c in CORES.items()}
NAMES = list(CORES)
LANES = [n for n in NAMES if ".g_ln[" in n]
DX, DY = G.CORE_TRACK_OFFSET
LAT = G.G
SMAX = G.CORE_INT_REACH_UM


def load(dump, tn):
    for ln in open(dump):
        d = json.loads(ln)
        if d["type"] == tn:
            return d
    raise SystemExit("type %s not in %s" % (tn, dump))


class Type:
    def __init__(self, d):
        self.tn, self.w, self.h, self.buses, self.ftsl = d["type"], d["w"], d["h"], d["buses"], d["ftsl"]
        bf = {b.get("face") for b in self.buses if b.get("face") in ("N", "S")}
        self.my = bf == {"S"}
        dummy = [dict(origin_um=[-1e6, -1e6], outline_um=[1, 1])]
        self.k0 = [G.ft_stations_macro(s, dummy, self.w, self.h, smax=SMAX) for s in self.ftsl]
        self.bw = G._bus_pts(self.buses, self.w, self.h)

    def cores(self, P, V):
        """hard_cores[] in the type frame (y mirror for S-bus types, as gen mirrored())."""
        o = []
        for i in NAMES:
            cw, ch = SIZE[i]
            x, y = P[i]
            e = G._core_view(SPEC, CORES[i], V.get(i), origin_um=[x, y], outline_um=[cw, ch], orient="R0",
                             track_offset_um=[DX, DY])
            if self.my:
                e["origin_um"] = [x, round(math.floor(round((self.h - (y + DY + ch) - DY) / LAT, 6)) * LAT, 4)]
                e["orient"] = "MX"
                e["track_offset_um"] = [DX, round((0.036 - ch) % 0.048, 4)]
            o.append(e)
        return o


def legal(T, o):
    bx = [(c["origin_um"][0] + c["track_offset_um"][0], c["origin_um"][1] + c["track_offset_um"][1],
           c["origin_um"][0] + c["track_offset_um"][0] + c["outline_um"][0],
           c["origin_um"][1] + c["track_offset_um"][1] + c["outline_um"][1]) for c in o]
    bad = 0
    for i, a in enumerate(bx):
        if a[0] < G.HC_EDGE_UM - 1e-6 or a[1] < G.HC_EDGE_UM - 1e-6 or a[2] > T.w - G.HC_EDGE_UM + 1e-6 or \
                a[3] > T.h - G.HC_EDGE_UM + 1e-6:
            bad += 1
        for b in bx[i + 1:]:
            if max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3]) < G.HC_GAP_UM - 1e-6:
                bad += 1
    return bad


def reach_excess(T, o):
    ex = 0.0
    cb = {ci: {t[4:] for tg in pp.values() for t in tg if t.startswith("bus:")} for ci, pp in G.CORE_CONNS[K].items()}
    for c in o:
        x0, y0 = c["origin_um"][0] + c["track_offset_um"][0], c["origin_um"][1] + c["track_offset_um"][1]
        x1, y1 = x0 + c["outline_um"][0], y0 + c["outline_um"][1]
        for bn in cb.get(c["inst"], ()):
            a = T.bw.get(bn)
            if a:
                ex += max(0.0, max(x0 - a[0], 0, a[0] - x1) + max(y0 - a[1], 0, a[1] - y1) - G.FT_STATION_MAX)
    return round(ex, 1)


def shaping(T, o, ents):
    """continuous terms: every core-pair / bus-core bundle length (pin centroid -> partner) over 0.6 x reach, weighted by
    bits; hcpl lanes within the reach of vn's hq / hw centroid (the vp glue sits there)."""
    pl = {c["inst"]: G._placed_groups(c) for c in o}
    s = 0.0
    bp = T.bw
    conns = G.CORE_CONNS[K]
    for a, ports in conns.items():
        for pa, tg in ports.items():
            ga = pl[a][1].get(pa)
            if not ga:
                continue
            for t in tg:
                kd, _, nm = t.partition(":")
                if kd == "bus" and nm in bp:
                    q = bp[nm]
                elif kd == "core" and nm in pl:
                    bx = pl[nm][0]
                    q = (min(max(ga[0], bx[0]), bx[2]), min(max(ga[1], bx[1]), bx[3]))
                else:
                    continue
                L = abs(ga[0] - q[0]) + abs(ga[1] - q[1])
                s += ga[2] * max(0.0, L - 0.6 * SMAX) * 0.05 + ga[2] * L * 0.002
    return s


def evaluate(T, P, V, full=True):
    o = T.cores(P, V)
    lg = legal(T, o)
    if lg:
        return 1e9 + 1e7 * lg, None
    fa = G.core_faces_away(K, o, T.w, T.h, T.buses)
    rx = reach_excess(T, o)
    ents, icyc = G.core_internal_stations(K, o, T.w, T.h, T.buses)
    ft = sum(max(0, G.ft_stations_macro(s, o, T.w, T.h, smax=SMAX) - T.k0[i]) for i, s in enumerate(T.ftsl)) \
        if full else 0
    bits = sum(len(e["regs_um"]) * e["bits"] for e in ents)
    key = (fa, rx, round(icyc + ft + bits / G.STATION_BITS_PER_CYCLE, 2))
    c = 1e7 * fa + 1e4 * rx + 1e5 * (icyc + ft + bits / G.STATION_BITS_PER_CYCLE) + shaping(T, o, ents)
    return c, dict(key=key, faces_away=fa, reach_excess=rx, int_cycles=icyc, ft_add=ft, station_bits=bits)


def xmirror(T, P, V):
    P2 = {}
    for i in NAMES:
        cw, _ = SIZE[i]
        x, y = P[i]
        P2[i] = [round(math.floor(round((T.w - (x + DX + cw) - DX) / LAT, 6)) * LAT, 4), y]
    V2 = {i: (None if V.get(i) else XV) for i in VIEWABLE}
    return P2, {i: v for i, v in V2.items() if v}


def anneal(T, P, V, iters, T0=3e4):
    cur, det = evaluate(T, P, V)
    best = (cur, {k: list(v) for k, v in P.items()}, dict(V), det)
    E_ = ["u_lf.u_vs", "u_lf.u_ve"]
    EC = E_ + ["u_lf.u_vsw", "u_lf.u_rxsf", "u_lf.u_rxsb", "u_lf.u_vq"]
    VN = ["u_lf.u_vn", "u_lf.u_vp.u_b0", "u_lf.u_vp.u_b1"]
    groups = [LANES, EC, EC + VN, NAMES, E_, VN, VN + LANES, ["u_lf.u_rxsf", "u_lf.u_rxsb"]] + [[n] for n in NAMES]
    for it in range(iters):
        Tt = T0 * (1 - it / iters) + 1
        oldP, oldV = None, dict(V)
        r = random.random()
        if r < 0.08:
            a, b = random.sample(LANES, 2)
            oldP = {a: list(P[a]), b: list(P[b])}
            P[a], P[b] = P[b], P[a]
        elif r < 0.13:
            i = random.choice(VIEWABLE)
            V[i] = None if V.get(i) else XV
            V = {k: v for k, v in V.items() if v}
        elif r < 0.14:
            oldP = {k: list(v) for k, v in P.items()}
            P2, V = xmirror(T, P, V)
            P.update(P2)
        else:
            g = random.choice(groups)
            oldP = {k: list(P[k]) for k in g}
            k_ = random.choice([1, 1, 1, 2, 3, 5, 10, 20, 40])
            dx, dy = LAT * k_ * random.choice([-1, 0, 1]), LAT * k_ * random.choice([-1, 0, 1])
            for k in g:
                P[k] = [round(P[k][0] + dx, 4), round(P[k][1] + dy, 4)]
        nc, nd = evaluate(T, P, V)
        if nc < cur or random.random() < math.exp(max(-50, (cur - nc) / Tt)):
            cur, det = nc, nd
            if cur < best[0]:
                best = (cur, {k: list(v) for k, v in P.items()}, dict(V), det)
        else:
            if oldP:
                P.update(oldP)
            V = oldV
    return best


def tmpl(T, c, order="A"):
    """structural seed (design frame, bus face N), window pair centre at x = c: the bus cores in the top band under the
    window -- ve at the edge over vs (vs N = ve ports + bus ports), vq W of ve at the edge (y W / u E / bus N), vn W of vq at
    the edge (lanes / store W, y E, bus N); store SRAMs under vn's centre; vsw E of vs; rxsf / rxsb under vs; the 16
    hcpl lanes on a lattice grid nearest vn's hq / hw ports."""
    Y1 = T.h - G.HC_EDGE_UM
    gap = 2 * LAT
    S = SIZE
    up = lambda v: math.ceil(round(v / LAT, 6)) * LAT
    dn = lambda v: math.floor(round(v / LAT, 6)) * LAT
    P = {}
    P["u_lf.u_ve"] = [dn(c - S["u_lf.u_ve"][0] / 2), dn(Y1 - S["u_lf.u_ve"][1] - DY)]
    P["u_lf.u_vs"] = [dn(c - S["u_lf.u_vs"][0] / 2), dn(P["u_lf.u_ve"][1] - gap - S["u_lf.u_vs"][1])]
    if order == "A":
        # top band [vn][vq][ve over vs]
        P["u_lf.u_vq"] = [dn(P["u_lf.u_ve"][0] - gap - S["u_lf.u_vq"][0]), dn(Y1 - S["u_lf.u_vq"][1] - DY)]
        P["u_lf.u_vn"] = [dn(P["u_lf.u_vq"][0] - gap - S["u_lf.u_vn"][0]), dn(Y1 - S["u_lf.u_vn"][1] - DY)]
    else:
        # top band [vn][ve over vs], vq under the vn / ve gap (y W -> vn, u E -> vs, bus N)
        P["u_lf.u_vn"] = [dn(P["u_lf.u_ve"][0] - gap - S["u_lf.u_vn"][0]), dn(Y1 - S["u_lf.u_vn"][1] - DY)]
        P["u_lf.u_vq"] = [dn(P["u_lf.u_ve"][0] - S["u_lf.u_vq"][0] / 2), dn(P["u_lf.u_ve"][1] - gap - S["u_lf.u_vq"][1])]
        if P["u_lf.u_vq"][0] + S["u_lf.u_vq"][0] + gap > P["u_lf.u_vs"][0]:
            P["u_lf.u_vq"][0] = dn(P["u_lf.u_vs"][0] - gap - S["u_lf.u_vq"][0])
        if P["u_lf.u_vq"][1] + S["u_lf.u_vq"][1] + gap > P["u_lf.u_vn"][1] and \
                P["u_lf.u_vq"][0] < P["u_lf.u_vn"][0] + S["u_lf.u_vn"][0] + gap:
            P["u_lf.u_vq"][1] = dn(P["u_lf.u_vn"][1] - gap - S["u_lf.u_vq"][1])
    # vsw E of vs and of ve's overhang, centres level (its N / S faces both go to vs: perpendicular, mirror-safe)
    P["u_lf.u_vsw"] = [up(max(P["u_lf.u_vs"][0] + S["u_lf.u_vs"][0], P["u_lf.u_ve"][0] + S["u_lf.u_ve"][0]) + gap),
                       dn(P["u_lf.u_vs"][1] + (S["u_lf.u_vs"][1] - S["u_lf.u_vsw"][1]) / 2)]
    # rxsf / rxsb centred under vs (their E / W faces both go up to vs / each other: perpendicular, mirror-safe)
    xr = dn(P["u_lf.u_vs"][0] + (S["u_lf.u_vs"][0] - S["u_lf.u_rxsf"][0]) / 2)
    P["u_lf.u_rxsf"] = [xr, dn(P["u_lf.u_vs"][1] - gap - S["u_lf.u_rxsf"][1])]
    P["u_lf.u_rxsb"] = [xr, dn(P["u_lf.u_rxsf"][1] - gap - S["u_lf.u_rxsb"][1])]
    vn = P["u_lf.u_vn"]
    sx = dn(vn[0] + S["u_lf.u_vn"][0] / 2 - S["u_lf.u_vp.u_b0"][0] / 2 - 2 * LAT)
    P["u_lf.u_vp.u_b0"] = [sx, dn(vn[1] - gap - S["u_lf.u_vp.u_b0"][1])]
    P["u_lf.u_vp.u_b1"] = [sx, dn(P["u_lf.u_vp.u_b0"][1] - gap - S["u_lf.u_vp.u_b1"][1])]
    # shift the band into the outline
    xs = [P[i][0] for i in P]
    xe = [P[i][0] + S[i][0] for i in P]
    sh = max(0.0, up(G.HC_EDGE_UM - min(xs))) - max(0.0, up(max(xe) - (T.w - G.HC_EDGE_UM - 1)))
    for i in P:
        P[i][0] = round(P[i][0] + sh, 4)
    # lanes: lattice grid sites nearest vn's W-face hq / hw pins, not overlapping anything placed
    lw, lh = S[LANES[0]]
    qx, qy = P["u_lf.u_vn"][0], P["u_lf.u_vn"][1] + S["u_lf.u_vn"][1] / 2
    pitch = up(lw + gap)
    sites = []
    for ix in range(int(T.w // pitch) + 1):
        for iy in range(int(T.h // pitch) + 1):
            x, y = G.HC_EDGE_UM + ix * pitch, G.HC_EDGE_UM + iy * pitch
            if x + lw > T.w - G.HC_EDGE_UM or y + lh > T.h - G.HC_EDGE_UM:
                continue
            sites.append((abs(x + lw - qx) + abs(y + lh / 2 - qy), x, y))
    sites.sort()
    boxes = [(P[i][0], P[i][1], P[i][0] + S[i][0], P[i][1] + S[i][1]) for i in P]
    k = 0
    for _, x, y in sites:
        if k == len(LANES):
            break
        b = (x, y, x + lw, y + lh)
        if all(max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3]) >= gap for a in boxes):
            P[LANES[k]] = [round(x, 4), round(y, 4)]
            boxes.append(b)
            k += 1
    return P


def main():
    dump, tn, seed, iters, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    init = sys.argv[6] if len(sys.argv) > 6 else "-"
    random.seed(seed)
    T = Type(load(dump, tn))
    P = {k: list(v[:2]) for k, v in SPEC["place"].items()}
    V = {}
    cw_ = sum(sum(b["window_um"]) / 2 for b in T.buses if b["name"] in ("leafup_o0", "leafdn_i0")) / 2
    if init.startswith("tmpl"):
        # tmplA / tmplC: structural seeds (see tmpl); tmplB / tmplD: the same x-mirrored (vn / vq / vs xm views)
        od = {"A": ("A", 0), "B": ("A", 1), "C": ("C", 0), "D": ("C", 1)}[init[4]]
        if not od[1]:
            P.update(tmpl(T, cw_, od[0]))
        else:
            P.update(tmpl(T, T.w - cw_, od[0]))
            P, V = xmirror(T, P, V)
    else:
        if init != "-":
            j = json.load(open(init))
            P.update({k: list(v) for k, v in j["place"].items()})
            V = dict(j.get("views", {}))
            if j.get("mirror"):
                P, V = xmirror(T, P, V)
    c0, d0 = evaluate(T, P, V)
    print("start", round(c0), d0, flush=True)
    b = anneal(T, P, V, iters)
    print("end", round(b[0]), b[3], flush=True)
    json.dump(dict(type=tn, place=b[1], views=b[2], key=b[3]["key"] if b[3] else None, detail=b[3], seed=seed,
                   init=init), open(out, "w"))


if __name__ == "__main__":
    main()
