#!/usr/bin/env python3
"""FRAME-SPINE-1113 (FRAME-FORMS-1, DIEVIEW-S81 F1): template seed for the S81 frame family col_h9 / col_h10.

    frame_spine_seed.py PLAN_OR_EXTRACT.json OUT_SEED.json [--types REGEX] [--report R.json]

ONE template, applied to every frame type as rules + per-type deltas.  Positions / orientations only: no core is
reshaped, no pin, window, port, RTL or outline changes.  Output = core_place.py --seed JSON {type: {inst: {origin_um,
orient}}} (core_place legalises it, re-sites internal stations and carries the taps that ride on cores).

TEMPLATE (type frame, um; lattice 4.32):
  x plan  W pair [17.28 .. 553.5] | ROM cols A 574.56, B 630.72 | CENTRE STREET 668.76 .. 738.72 (69.96, holds the type
          clock tap x 725.76) | ROM cols B' 738.72, A' 794.88 | E pair [855.36 .. 1391.58] | E margin 51.3.
          The former empty east strip (290 um) becomes the SPINE: both pairs' cfg ROMs stand beside their own pair,
          so every E-W street under an element row is free of the 14 + 3 small cores that stood in it.
  row unit (bottom to top, y_s = street bottom):
          t band      y_s .. +30.24      slot station t (x 717.12) and its payload (x 613.44) at the spine mouth
          channel     43.2                station -> bank relays
          bs band     y_s+73.44 .. +99.36 bank of the pair, centred between the two S pin clumps (pair x + 276.48)
          apron       51.84               CLEAR: bs N pins (604) fan to 2 x 608 element S pins (R-STREET-1: 1820/37.5)
          elements    y_e = y_s + 151.2, 221.4 tall
          N street    46.44               bn (8.64 tall) 20.5 above the N pins
          ROM block   col A 3 ROMs, col B 4 ROMs at y_e - 4.32 + r x 82.08 (19.1 um slot under every ROM S pin face)
          sequencer   in the apron corner at the spine end (W unit x 514.08 R180, E unit x 876.96 MX), q face 43.2 from
                      col A, cfg face down into the street
  bf unit  ROM band 64.8 (4 ROMs | 43.2 | bfp seq | t | 3 ROMs | payload) + 43.2 street + bf group (W half-group moved
          so the front-roots faces have 43.2 streets)
  nodes    E zone beside the bf group (3 cols x 2 rows, 43.2 streets) and the outer ends of the row streets below
          the apron; assigned by connectivity.
Per-type deltas: unit order and y come from each type's own base order (rows / bf sorted by base y); cores the template
does not know (cf, rstg) keep their base spot and are legalised by core_place.
"""
import json, re, sys, gzip, itertools, random

G = 8.64          # G0C hard_cores: every core origin on the 8.64 um lattice
XW, XE, DHE = 17.28, 864.0, 267.84
COL = {"W": (578.88, 639.36), "E": (803.52, 743.04)}   # col B' 17.28 off the type clock tap x 725.76   # cols A, B, C: abutted to the pair and to each other
SEQX = {"W": 518.4, "E": 993.6}   # <= 405 um to the far half's cfg pins and to the farthest ROM
SEQO = {"W": "R0", "E": "R0"}      # no flips: a flipped seq puts its M4 pins off the plan tracks
TX, PX = 699.84, 570.24
S_STREET, ROW_PITCH = 138.24, 406.08
ROMP = 69.12
BF_BAND = 103.68
REACH = 395.0


def snap(v):
    return round(round(v / G) * G, 3)


def short(inst):
    return inst.split(".", 1)[1]


def roles(t):
    C = {short(c["inst"]): c for c in t["hard_cores"]}
    pairs = {}
    for n, c in C.items():
        m = re.match(r"u_e(\d+)\.u_([we])$", n)
        if m:
            pairs.setdefault(m.group(1), {})[m.group(2)] = c
    rows = {}
    for k, p in pairs.items():
        rows.setdefault(round(p["w"]["origin_um"][1], 1), []).append(k)
    rows = [sorted(v, key=lambda k: pairs[k]["w"]["origin_um"][0]) for _, v in sorted(rows.items())]
    bfs = sorted((n for n, c in C.items() if c["module"] == "dsfd_bf_front_roots"), key=lambda n: C[n]["origin_um"][1])
    return C, pairs, rows, bfs


def adj(conns):
    A = {}
    for inst, pins in (conns or {}).items():
        a = short(inst)
        for pin, dsts in pins.items():
            for d in dsts:
                if d.startswith("core:"):
                    A.setdefault(a, {}).setdefault(d[5:], 0)
                    A[a][d[5:]] += 1
    return A


def partner_insts(A, C, a):
    out = set()
    for d in A.get(a, {}):
        dn = d.split(".", 1)[1] if d.split(".", 1)[0].startswith("u_r") else d
        cand = [n for n in C if dn.startswith(n + ".") or dn == n]
        if cand:
            out.add(max(cand, key=len))
    for b, ds in A.items():
        for d in ds:
            dn = d.split(".", 1)[1] if d.split(".", 1)[0].startswith("u_r") else d
            if dn.startswith(a + "."):
                out.add(b)
    return out


PINS = {}          # module -> {pin group: (x, y) centroid in the core frame}
REPO = [None]


def pin_xy(c, pin):
    m = c["module"]
    if m not in PINS:
        g = {}
        try:
            import os
            f = os.path.join(REPO[0], c["pins_file"])
            if not os.path.exists(f):
                f = os.path.join(REPO[0], "physical/die_plan/s81", c["pins_file"])
            acc = {}
            for q in json.load(open(f))["pins"]:
                acc.setdefault(q["name"].split("[")[0], []).append((q["x"], q["y"]))
            g = {k: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)) for k, v in acc.items()}
        except Exception:
            g = {}
        PINS[m] = g
    return PINS[m].get(pin, (c["outline_um"][0] / 2, c["outline_um"][1] / 2))


def seed_type(tn, t, conns, log):
    W, H = t["outline_um"]
    C, pairs, rows, bfs = roles(t)
    A = adj(conns)
    seed = {}

    def put(n, x, y, o=None):
        c = C[n]
        seed[c["inst"]] = {"origin_um": [round(x, 3), round(y, 3)], "orient": o or c.get("orient", "R0")}

    # ---- units in base order -------------------------------------------------------------------------------
    units = [("row", r, min(pairs[k]["w"]["origin_um"][1] for k in r)) for r in rows] + \
            [("bf", b, C[b]["origin_um"][1]) for b in bfs]
    units.sort(key=lambda u: u[2])
    # t stations -> unit: by adjacency to the unit's sequencers / front roots, else by base y order
    tnames = sorted((n for n in C if re.match(r"u_t\d+$", n)), key=lambda n: C[n]["origin_um"][1])
    seq_of = {}
    for n, c in C.items():
        m = re.match(r"u_s(\d+)$", n)
        if m:
            seq_of[m.group(1)] = n
    bf_seq = {}
    for k, s in seq_of.items():
        if "bfp" in C[s]["module"]:
            ps = partner_insts(A, C, s)
            tgt = [b for b in bfs if b in ps] or [b for b in bfs if b == "u_e" + k]
            if tgt and tgt[0] not in bf_seq:
                bf_seq[tgt[0]] = k
    left = [b for b in bfs if b not in bf_seq]
    for k, s in seq_of.items():
        if "bfp" in C[s]["module"] and k not in bf_seq.values() and left:
            bf_seq[left.pop(0)] = k
    t_of = {}
    for u in units:
        want = set()
        if u[0] == "row":
            want = {seq_of[k] for k in u[1] if k in seq_of}
        else:
            want = {u[1]} | ({seq_of[bf_seq[u[1]]]} if u[1] in bf_seq else set())
        best = None
        for tn_ in tnames:
            if tn_ in t_of.values():
                continue
            if partner_insts(A, C, tn_) & want:
                best = tn_
                break
        if best:
            t_of[u[1] if u[0] == "bf" else tuple(u[1])] = best
    spare_t = [n for n in tnames if n not in t_of.values()]
    for u in units:
        key = u[1] if u[0] == "bf" else tuple(u[1])
        if key not in t_of and spare_t:
            t_of[key] = spare_t.pop(0)

    # ---- vertical solve ------------------------------------------------------------------------------------
    need = 0.0
    hs = []
    for i, u in enumerate(units):
        if u[0] == "row":
            h = ROW_PITCH
        else:
            h = (BF_BAND if u[1] in bf_seq or (u[1] in t_of) else 43.2) + 198.72
            if i < len(units) - 1:
                h += 43.2                       # street above a bf group that is not the top unit
        hs.append(h)
        need += h
    # the top unit: a row keeps its N street inside ROW_PITCH (46.44); a bf group needs >= 43.2 to the N face
    top_m = 43.2 if units[-1][0] == "bf" else 0.0
    slack = H - need - top_m
    m0 = 43.2 if slack >= 43.2 else 8.64 * int(max(slack, 0) / 8.64)
    info = {"units": [(u[0], u[1]) for u in units], "need": round(need, 2), "slack": round(slack, 2), "m0": m0,
            "top_margin": round(H - need - m0, 2), "t_of": {str(k): v for k, v in t_of.items()}, "bf_seq": bf_seq}
    if slack < 0:
        log("  %s: NO FIT vertically (need %.1f + %.1f > %.1f)" % (tn, need, top_m, H))
        info["nofit"] = True
        return {}, info
    y = m0
    node_sites = []
    row_sites = set()
    rg_sites = []
    for i, u in enumerate(units):
        if u[0] == "row":
            ys, ye = y, y + S_STREET
            for side, k in zip(("W", "E"), u[1]):
                px = XW if side == "W" else XE
                put("u_e%s.u_w" % k, px, ye)
                put("u_e%s.u_e" % k, px + DHE, ye)
                if "u_bs" + k in C:
                    put("u_bs" + k, px + 276.48, ye - 77.76, "R0")
                if "u_bn" + k in C:
                    put("u_bn" + k, px + ((138.24 if side == "W" else 95.04) if i + 1 < len(units) and units[i + 1][0] == "bf" else 311.04),
                        ye + 241.92, "R0")      # 20.5 um over the N pins: sparse face (2.1 pins / um), tap-legal slot
                if k in seq_of:
                    put(seq_of[k], SEQX[side], ye - 95.04, SEQO[side])
                cols = COL[side]
                roms = sorted((n for n in C if re.match(r"u_c%s_\d+$" % k, n)), key=lambda n: int(n.rsplit("_", 1)[1]))
                for j, n in enumerate(roms):
                    # ROM pins: 43 + 43 M4 pins at the bottom 5 um of the W and E edges.  Col A (4 ROMs, next to the pair)
                    # and col B (3 ROMs, at the street) keep 17.28+ um slots on both sides (COORD ruling 11-13: sparse
                    # faces may face a tap-legal slot); N-S the ROMs stand 6.2 um apart (pinless faces)
                    cx, r = (cols[0], j) if j < 4 else (cols[1], j - 4)
                    if side == "E":
                        # E unit reach (<= 405 um to the seq): col A' rows -1..2, col B' rows 0..1, 7th in the corner
                        cx, r = (cols[0], j - 1) if j < 4 else (cols[1], j - 4)
                    if side == "E" and j == 6:
                        # E unit: the pin groups sit at 143 / 411 of 536, so its seq stands 130 um into the pair and the
                        # 7th ROM would be 429 um from it at the top of col B: it stands in the street corner beside
                        # the seq instead (43.2 off the seq q face, outside the bank fan)
                        put(n, px + 43.2, ye - 112.32)
                    else:
                        put(n, cx, ye - 51.84 + r * ROMP)
            tk = t_of.get(tuple(u[1]))
            if tk:
                put(tk, TX, ys, "R0")
                if tk + "__payload" in C:
                    put(tk + "__payload", PX, ys, "R0")
            # row-street end sites, below the apron: 2 W of the hw pin group, 4 E (1 W of the bank, 3 E of it at 17.28 um
            # slots: node side faces are sparse or pinless)
            node_sites += [(x_, max(ys + G, 43.2)) for x_ in (60.48, 146.88, 1080.0, 1218.24, 1278.72, 1339.2)]
            row_sites.update(node_sites[-6:])
            y += hs[i]
        else:
            b = u[1]
            has_band = b in bf_seq or b in t_of
            yb = y + (BF_BAND if has_band else 43.2)
            m = re.match(r"u_e(\d+)$", b)
            B = m.group(1)
            ex = C[b]["origin_um"][0]
            put(b, ex, yb)
            for side in ("w", "e"):
                grp = [n for n in C if n.startswith("u_e%s%s." % (B, side))]
                if not grp:
                    continue
                c3 = [n for n in grp if n.endswith(".u_c")][0]
                c3x = C[c3]["origin_um"][0]
                c3w = C[c3]["outline_um"][0]
                if side == "w":
                    gap = ex - (c3x + c3w)
                    dx = -snap(max(0.0, 43.2 - gap) + 4.31) if gap < 43.2 else 0.0
                else:
                    gap = c3x - (ex + C[b]["outline_um"][0])
                    dx = snap(max(0.0, 43.2 - gap) + 4.31) if gap < 43.2 else 0.0
                for n in grp:
                    put(n, C[n]["origin_um"][0] + dx, yb + (C[n]["origin_um"][1] - C[b]["origin_um"][1]))
            if has_band:
                yr = y
                k = bf_seq.get(b)
                sx = snap(ex)
                tx = snap(sx + 30.24 + 43.2 + 4.31)        # seq | station | 7th ROM | payload
                if k:
                    put(seq_of[k], sx, yr, "R0")
                    roms = sorted((n for n in C if re.match(r"u_c%s_\d+$" % k, n)),
                                  key=lambda n: int(n.rsplit("_", 1)[1]))
                    wx = snap(sx - 43.2 - 38.04 - 4.31)
                    exr = snap(tx + 84.24 + 17.28 + 4.31)
                    for j, n in enumerate(roms):
                        put(n, wx - j * 60.48 if j < 6 else exr, yr)
                tk = t_of.get(b)
                if tk:
                    put(tk, tx, yr + 25.92, "R0")
                    if tk + "__payload" in C:
                        put(tk + "__payload", snap(snap(tx + 84.24 + 17.28 + 4.31) + 38.04 + 17.28 + 4.31), yr + 34.56, "R0")
            # node sites in the E zone beside the bf group
            for cx in (1183.68, 1270.08, 1356.48):
                rows_ = (yb + 25.92, yb + 146.88) if has_band and yb + 146.88 + 77.76 + 43.2 <= H + 0.01 else (yb, yb + 120.96)
                for ry in rows_:
                    node_sites.append((cx, ry))
                if has_band and rows_[0] > yb and i > 0 and units[i - 1][0] == "row":
                    node_sites.append((cx, y + 8.64))      # band row: links the E zone to the row street below
            if i > 0 and units[i - 1][0] == "row":
                rg_sites.append((1036.8, yb - 77.76))
            y += hs[i]
    rgs = sorted(n for n in C if C[n]["module"] == "dsfd_rstg")
    for n, (x_, y_) in zip(rgs, rg_sites):
        put(n, x_, y_)
    # ---- internal stations: which cores own their ends (base), and the length each may have ---------------------
    def owner(pt):
        for n, c in C.items():
            (x0, y0), (w, h) = c["origin_um"], c["outline_um"]
            if x0 - 1.0 <= pt[0] <= x0 + w + 1.0 and y0 - 1.0 <= pt[1] <= y0 + h + 1.0:
                return n
        return None
    stn = []
    for s_ in t.get("internal_stations") or []:
        a_, b_ = owner(s_["from_um"]), owner(s_["to_um"])
        b0 = abs(s_["from_um"][0] - s_["to_um"][0]) + abs(s_["from_um"][1] - s_["to_um"][1])
        lim = max(b0, (len(s_.get("regs_um") or []) + 1) * REACH * 0.8) - 4.32   # core_place init_limits
        stn.append((a_, b_, s_["from_um"], s_["to_um"], lim, s_["conn"]))
    # ---- nodes by connectivity ------------------------------------------------------------------------------
    nodes = sorted((n for n in C if "node" in C[n]["module"]), key=lambda n: int(re.sub(r"\D", "", n)))
    if nodes:
        if len(node_sites) < len(nodes):
            log("  %s: %d nodes, %d sites: the rest stay at base (core_place legalises)" % (tn, len(nodes), len(node_sites)))
        links = []          # (node a, pin offset a, node b, pin offset b): node-to-node links, pin to pin
        seen_l = set()
        for a in nodes:
            for pin, dsts in ((conns or {}).get(C[a]["inst"]) or {}).items():
                for d in dsts:
                    if not d.startswith("core:"):
                        continue
                    dn = d[5:].split(".", 1)[1]
                    b = next((n for n in nodes if dn.startswith(n + ".")), None)
                    if b and b != a and (a, pin, b) not in seen_l and (b, dn[len(b) + 1:], a) not in seen_l:
                        seen_l.add((a, pin, b))
                        links.append((a, pin_xy(C[a], pin), b, pin_xy(C[b], dn[len(b) + 1:])))
        base = {n: C[n]["origin_um"] for n in nodes}
        win = {}
        for b_ in t["buses"]:
            lo, hi = b_["window_um"]; m_ = (lo + hi) / 2
            win[b_["name"]] = {"S": (m_, 0.0), "N": (m_, H), "W": (0.0, m_), "E": (W, m_)}[b_["face"]]
        blinks = []
        for a in nodes:
            for pin, dsts in ((conns or {}).get(C[a]["inst"]) or {}).items():
                if pin in ("rs", "rst_n", "clk", "ck"):
                    continue
                for d in dsts:
                    if d.startswith("bus:") and d[4:] in win:
                        blinks.append((a, win[d[4:]]))
        use = nodes[:len(node_sites)]

        def cost(asg):
            s = 0.0
            for a, oa, b, ob in links:
                if a in asg and b in asg:
                    pa, pb = node_sites[asg[a]], node_sites[asg[b]]
                    d = abs(pa[0] + oa[0] - pb[0] - ob[0]) + abs(pa[1] + oa[1] - pb[1] - ob[1])
                    d0 = abs(base[a][0] + oa[0] - base[b][0] - ob[0]) + abs(base[a][1] + oa[1] - base[b][1] - ob[1])
                    # core_place measures these links with its own pin model (seen up to 50 um longer than the pin-group centroids):
                    # keep 60 um of margin under the limit
                    s += d + (500.0 * (d - max(d0, 405.0) + 60.0) if d > max(d0, 405.0) - 60.0 else 0.0)
            for a, wp in blinks:               # a node -> window link stays no longer than in the base plan
                if a in asg:
                    p = node_sites[asg[a]]
                    d = abs(p[0] - wp[0]) + abs(p[1] - wp[1])
                    d0 = abs(base[a][0] - wp[0]) + abs(base[a][1] - wp[1])
                    s += 0.2 * d + (50.0 * (d - max(d0, 405.0)) if d > max(d0, 405.0) else 0.0)
            for a_, b_, fa, fb, lim, _ in stn:      # a station keeps its register count: its ends stay in reach
                if a_ in asg or b_ in asg:
                    def pos(n, f):
                        if n in asg:
                            q = node_sites[asg[n]]
                            return (q[0] + f[0] - base[n][0], q[1] + f[1] - base[n][1])
                        if n is not None and C[n]["inst"] in seed:
                            q = seed[C[n]["inst"]]["origin_um"]
                            return (q[0] + f[0] - C[n]["origin_um"][0], q[1] + f[1] - C[n]["origin_um"][1])
                        return f
                    pa, pb = pos(a_, fa), pos(b_, fb)
                    d = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
                    if d > lim:
                        s += 200.0 * (d - lim)
            for a in asg:                  # stay near the base spot when the tree does not care
                p = node_sites[asg[a]]
                s += 0.05 * (abs(p[0] - base[a][0]) + abs(p[1] - base[a][1]))
            return s
        rnd = random.Random(1113)
        best = None
        for trial in range(400):
            idx = list(range(len(node_sites)))
            rnd.shuffle(idx)
            asg = {n: idx[i] for i, n in enumerate(use)}
            free = idx[len(use):]
            c = cost(asg)
            imp = True
            while imp:
                imp = False
                for a, b in itertools.combinations(use, 2):
                    asg[a], asg[b] = asg[b], asg[a]
                    c2 = cost(asg)
                    if c2 < c - 1e-9:
                        c = c2; imp = True
                    else:
                        asg[a], asg[b] = asg[b], asg[a]
                for a in use:
                    for fi in range(len(free)):
                        old = asg[a]
                        asg[a], free[fi] = free[fi], old
                        c2 = cost(asg)
                        if c2 < c - 1e-9:
                            c = c2; imp = True
                        else:
                            free[fi], asg[a] = asg[a], old
            if best is None or c < best[0]:
                best = (c, dict(asg))
        # polish (hand rule): shorten the longest node-to-node link by pairwise swaps while no station / window limit
        # gets worse (a cross-row link wants its two nodes in one column)
        asg = dict(best[1])

        def worst(as_):
            m = 0.0
            for a_, oa, b_, ob in links:
                if a_ in as_ and b_ in as_:
                    pa, pb = node_sites[as_[a_]], node_sites[as_[b_]]
                    m = max(m, abs(pa[0] + oa[0] - pb[0] - ob[0]) + abs(pa[1] + oa[1] - pb[1] - ob[1]))
            return m

        def hard(as_):          # the penalty part of the cost only (limits), without the plain length terms
            return cost(as_) - sum(1 for _ in ())
        imp = True
        while imp:
            imp = False
            w0, c0 = worst(asg), cost(asg)
            for a_, b_ in itertools.combinations(use, 2):
                asg[a_], asg[b_] = asg[b_], asg[a_]
                if worst(asg) < w0 - 1.0 and cost(asg) < c0 + 2000.0:
                    imp = True
                    break
                asg[a_], asg[b_] = asg[b_], asg[a_]
        if len(use) <= 6 and len(use) == len(nodes):
            # small trees: exact minimax over all sites (station limits kept), ties by the cost above
            def stn_ok(as_):
                for a_, b_, fa, fb, lim, _ in stn:
                    for n_, f_, o_ in ((a_, fa, fb), (b_, fb, fa)):
                        if n_ in as_ and (b_ if n_ == a_ else a_) is None:
                            q = node_sites[as_[n_]]
                            if abs(q[0] + f_[0] - base[n_][0] - o_[0]) + abs(q[1] + f_[1] - base[n_][1] - o_[1]) > lim - 8.64:
                                return False
                return True
            bb = (worst(asg), asg) if stn_ok(asg) else None
            cand = [i_ for i_, q_ in enumerate(node_sites) if 1000.0 <= q_[0] <= 1340.0 and q_ in row_sites]   # E row-street ends
            for perm in itertools.permutations(cand, len(use)):
                as_ = dict(zip(use, perm))
                if not stn_ok(as_):
                    continue
                w_ = worst(as_)
                if bb is None or w_ < bb[0] - 1e-6:
                    bb = (w_, as_)
            if bb:
                asg = bb[1]
        info["node_worst_link"] = round(worst(asg), 1)
        for n, si in asg.items():
            put(n, node_sites[si][0], node_sites[si][1])
        info["node_cost"] = round(best[0], 1)
        info["node_links"] = len(links)
    over = []
    for a_, b_, fa, fb, lim, cn in stn:
        def pos2(n, f):
            if n is not None and C[n]["inst"] in seed:
                q = seed[C[n]["inst"]]["origin_um"]
                return (q[0] + f[0] - C[n]["origin_um"][0], q[1] + f[1] - C[n]["origin_um"][1])
            return f
        pa, pb = pos2(a_, fa), pos2(b_, fb)
        d = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
        if d > lim:
            over.append((cn, a_, b_, round(d), round(lim)))
    info["stations_over"] = over
    info["seeded"] = len(seed)
    info["unseeded"] = sorted(n for n in C if C[n]["inst"] not in seed)
    return seed, info


def main():
    a = sys.argv[1:]
    src, out = a[0], a[1]
    rx = re.compile(a[a.index("--types") + 1]) if "--types" in a else re.compile(r"col_h")
    D = json.load(gzip.open(src) if src.endswith(".gz") else open(src))
    if "partition_types" in D:
        types = D["partition_types"]
        cc = json.load(open(a[a.index("--conns") + 1]))
        import os
        REPO[0] = os.path.abspath(os.path.join(os.path.dirname(a[a.index("--conns") + 1]), "..", "..", ".."))
    else:
        types = D["types"]; cc = D["conns"]
        for m_, v_ in D["pins"].items():
            PINS[m_] = {k: ((g["x"][0] + g["x"][1]) / 2, (g["y"][0] + g["y"][1]) / 2) for k, g in v_["groups"].items()}
    seeds, rep, cache = {}, {}, {}
    for tn, t in sorted(types.items()):
        if not tn.startswith("col_h") or not rx.search(tn):
            continue
        base = tn.split("__pv")[0]
        if base in cache:            # all pv types of one base share one layout: same seed, renamed
            s0, info = cache[base]
            s = {k: v for k, v in s0.items()}
        else:
            s, info = seed_type(tn, t, cc.get(base) or cc.get(tn), lambda m: print(m))
            cache[base] = (s, info)
        if s:
            seeds[tn] = s
        rep[tn] = info
    json.dump(seeds, open(out, "w"), indent=1)
    if "--report" in a:
        json.dump(rep, open(a[a.index("--report") + 1], "w"), indent=1)
    done = {}
    for tn, info in rep.items():
        b = tn.split("__pv")[0]
        if b not in done:
            done[b] = info
            print("%-36s seeded %3s  slack %7.2f m0 %5.2f top %6.2f  unseeded %s  %s" % (
                b, info.get("seeded"), info["slack"], info["m0"], info["top_margin"], info.get("unseeded"),
                ("NOFIT" if info.get("nofit") else "") + (" STN_OVER %s" % info["stations_over"] if info.get("stations_over") else "")))


if __name__ == "__main__":
    main()
