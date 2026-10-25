#!/usr/bin/env python3
"""B2n = B2m + OWNER DECISION 12 (2026-10-24 21:31): partition feedthroughs on <= M7 with registered stations every
<= 405 um; M8/M9 reserved for the die clock spine, die reset and PG.  Derived deterministically from B2m (B2m stays):

    python3 physical/die_plan/hbm_arch/b2n.py [--src B2m] [--out B2n]

  1. layers   every type face drops its M8/M9 third pin layer (face_layers -> E/W [M6, M4], N/S [M7, M5]); every port
              drops M8/M9; die layer_budget.die_use loses ft_reserved (M8/M9 = clock spine / reset / PG only).
  2. windows  ports re-windowed for 2 pin layers: each port's window grows to width / PIN_DENS um (<= the 6 pins/um
              face budget with PG-band slack), then every face line is re-packed in one pass (isotonic least-squares
              shift, order kept, die-IO ports fixed, each port inside both abutting faces).  Mirror pairs stay mirror
              images (the packing is mirror-equivariant), so one pin table per type still holds.
  3. reach    die reach_um and budgets.ft_station_max_um = 405 (owner reach405; repeaters inside a hop as before).
  4. stations every ft slot's stations are re-derived on its route (type frame) with hops <= HOP, sited off the hard
              cores (cores_b2.RelayRouter / free_point: macro-free relay channels); internal_stations[] (R3-INTERNAL)
              re-derived the same way, plus new entries for every core link now over the 405-um limit.
  5. latency  plan latency table recomputed from the new stations (schema.Plan.lane_latency).
Reset = decision 13 neighbour wavefront (reset_tree.py release=wavefront; hard reset pins on a face toward a soft
neighbour); the clock H-tree (M8/M9) is
re-derived on the moved partition rects (b2m.clock: same symmetric binary H-tree on M8/M9).
"""
import argparse
import json
import math
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import schema as S  # noqa: E402
import check as CK  # noqa: E402
from cores_b2 import RelayRouter, free_point  # noqa: E402

SIDECARS = ["census_map.json", "core_conns.json", "cores_b2.json", "hbm_rows.json", "cores", "inputs"]
DIE_ONLY = {"M8", "M9"}
REACH = 405.0
HOP = 360.0          # station spacing (check.py: hop <= 405; xdie reach check: hop <= 0.9 x reach 405 = 364.5)
PIN_DENS = 5.6       # pins / um per port window on 2 layers (budget 6 / um, PG-band and rounding slack)
GAP = 0.48           # um between packed windows
SNAP = 0.008         # window ends on a 0.008-um grid (divides the 8.64 lattice: mirror images stay exact)
MIN_WIN = 8.64       # smallest window: one partition PG period on every pin layer (a 1-2 bit port needs a free track)
# 2-layer faces that cannot carry their abutting traffic: (grown type, shrunk neighbour type, um moved, reason).  The
# grown type gains the strip on its type-frame W face, so all its contents / taps / cores keep their DIE positions.
BOUNDARY_MOVES = [("q_su10", "q_spu0", 216.0,
                   "hub<->su10 N face carries 2998+1719+1615+514+514+268 b = 1363 um at 5.6 pins/um on M7/M5 vs "
                   "1166 um of hub overlap; spu0 (soft, no cores) gives 216 um (its hub face needs 1087 of 2290 um)"),
                  ("q_su30", "q_spu1", 216.0, "hub<->su30 S face: same traffic as su10 (mirror in y); spu1 soft")]


def snap(v):
    return round(round(v / SNAP) * SNAP, 4)


def move_boundaries(plan, log):
    parts = plan["partitions"]
    T = plan["partition_types"]
    for grow, shrink, d, why in BOUNDARY_MOVES:
        tg, ts = T[grow], T[shrink]
        assert not ts.get("hard_cores"), f"{shrink} has hard cores: shrinking it needs a re-place"
        tg["outline_um"][0] = round(tg["outline_um"][0] + d, 4)
        ts["outline_um"][0] = round(ts["outline_um"][0] - d, 4)

        def sh(xy):
            xy[0] = round(xy[0] + d, 4)
        for hc in tg.get("hard_cores", []):
            sh(hc["origin_um"])
        for c in tg.get("contents", []):
            if "origin_um" in c:
                sh(c["origin_um"])
        for k in ("clock", "reset"):
            if "tap_um" in tg.get(k, {}):
                sh(tg[k]["tap_um"])
        for tp in tg.get("clock", {}).get("taps", []):
            if "xy" in tp:
                sh(tp["xy"])
        for e in tg.get("internal_stations", []):
            sh(e["from_um"]); sh(e["to_um"])
            for r in e["regs_um"]:
                sh(r)
        for sl in tg.get("ft_slots", []):
            for r in sl.get("regs_um", []):
                sh(r)
            sl.pop("bit_sites_um", None)
        for k in ("clock", "reset"):
            if "tap_um" in ts.get(k, {}):
                ts[k]["tap_um"][0] = round(min(ts[k]["tap_um"][0], ts["outline_um"][0] / 2), 4)
        for p in parts:
            if p["type"] == grow and p.get("orient", "R0") in ("R0", "MX"):
                p["origin_um"][0] = round(p["origin_um"][0] - d, 4)
            if p["type"] == shrink and p.get("orient", "R0") in ("MY", "R180"):
                p["origin_um"][0] = round(p["origin_um"][0] + d, 4)
        log.append(f"boundary {grow} +{d:g} / {shrink} -{d:g} um ({why})")


LANE_DELTA = HERE / "B2n_inputs" / "lane_delta.json"
OPPF = {"E": "W", "W": "E", "N": "S", "S": "N"}
FACE_LAYERS = {"N": ["M7", "M5"], "S": ["M7", "M5"], "E": ["M6", "M4"], "W": ["M6", "M4"]}


def _mir(n):
    return "NE_" + n[3:] if n.startswith("NW_") else "NW_" + n[3:] if n.startswith("NE_") else n


def _adjacency(P, minc=400.0):
    """partition adjacency on the current rects: adj[a][b] = (face of a, lo, hi) of the shared segment (um)."""
    R = {n: P.rect(n) for n in P.parts}
    adj = defaultdict(dict)
    for a, (x0, y0, x1, y1) in R.items():
        for b, (a0, b0, a1, b1) in R.items():
            if a == b:
                continue
            if abs(x1 - a0) < 0.01 and min(y1, b1) - max(y0, b0) > minc:
                adj[a][b] = ("E", max(y0, b0), min(y1, b1)); adj[b][a] = ("W", max(y0, b0), min(y1, b1))
            if abs(y1 - b0) < 0.01 and min(x1, a1) - max(x0, a0) > minc:
                adj[a][b] = ("N", max(x0, a0), min(x1, a1)); adj[b][a] = ("S", max(x0, a0), min(x1, a1))
    return R, adj


def _lane_slots(P, lid):
    """[(part, slot name)] crossed by lane lid (the ft slot of every intermediate partition)."""
    out = []
    for pid in P.lanes[lid]["ports"][:-1]:
        d = P.ports[pid]["dst"]
        out.append((d["part"], d["bus"][:-2]))
    return out


def lane_delta(plan, log, path=LANE_DELTA):
    """HBM-BIND native-bind lane capacity (B2n_inputs/lane_delta.json, from b2_delays.json capacity_over / no_lane):
    widen lanes (ports along the lane, end buses, ft slots in every crossed type; a mirrored pair Lx / Lxm takes the max
    of its two needs, so replicated types keep one bus / slot width) and add new lanes (Dijkstra over abutting soft
    partitions, gen_arch.shortest; mirrored NW <-> NE with shared bus / slot names in replicated types, 'm' names in
    single-instance ones, as emit_mirror).  Windows are provisional: rewindow / enforce_mirror place them."""
    import gen_arch as GA
    D = json.loads(Path(path).read_text())
    P = S.Plan(plan)
    T = plan["partition_types"]
    ports = {p["id"]: p for p in plan["ports"]}
    lanes = {l["id"]: l for l in plan["lanes"]}

    def tbus(part, name):
        return next(b for b in T[P.parts[part]["type"]]["buses"] if b["name"] == name)

    def tslot(part, name):
        return next(s for s in T[P.parts[part]["type"]]["ft_slots"] if s["name"] == name)

    def set_width(lid, w):
        L = lanes[lid]
        for pid in L["ports"]:
            ports[pid]["width"] = w
        p0, p1 = ports[L["ports"][0]], ports[L["ports"][-1]]
        tbus(p0["src"]["part"], p0["src"]["bus"])["width"] = w
        tbus(p1["dst"]["part"], p1["dst"]["bus"])["width"] = w
        for part, sn in _lane_slots(P, lid):
            tslot(part, sn)["width"] = w

    rows = []
    for e in D["widen"]:
        for lid, w in zip(e["lanes"], e["width"]):
            for x in (lid, lid + "m"):
                if x not in lanes:
                    continue
                w0 = int(ports[lanes[x]["ports"][0]]["width"])
                assert w >= w0, f"lane_delta: {x} would shrink {w0} -> {w}"
                if w > w0:
                    set_width(x, w)
                    rows.append(f"{x} {w0}->{w}")
                if e.get("place") == "high":      # desired window at the high end of every face it crosses (order hint
                    for pid in lanes[x]["ports"]:  # for rewindow: keeps the neighbours' windows where they were)
                        pr = ports[pid]
                        _, a1, b1 = CK.face_line(P.rect(pr["src"]["part"]), pr["face"])
                        _, a2, b2 = CK.face_line(P.rect(pr["dst"]["part"]), S.OPP[pr["face"]])
                        L_ = max(S.port_pins_count(pr) / PIN_DENS + 0.5, MIN_WIN)
                        hi = min(b1, b2) - 0.5
                        pr["window_um"] = [snap(hi - L_), snap(hi)]
    # ---- new lanes
    R, adj = _adjacency(P)
    hard = {n for n in P.parts if T[P.parts[n]["type"]].get("hard")}
    nxt = 1 + max(int(l[1:].rstrip("m")) for l in lanes)
    added = []
    for e in D["new"]:
        i = nxt
        nxt += 1
        a, b = e["src"], e["dst"]
        pth = [a] + list(e["via"]) + [b] if e.get("via") else GA.shortest(R, adj, P.parts, a, b, hard)
        if pth is None:
            raise SystemExit(f"lane_delta: no path {a}->{b}")
        paths = [pth] + ([[_mir(x) for x in pth]] if e.get("mirror") else [])
        for mi, pp in enumerate(paths):
            for x, y in zip(pp, pp[1:]):
                assert y in adj[x], f"lane_delta: {x} and {y} do not abut ({pp})"
            for h in range(1, len(pp) - 1):
                assert adj[pp[h - 1]][pp[h]][0] != OPPF[adj[pp[h]][pp[h + 1]][0]], f"lane_delta: U-turn at {pp[h]} ({pp})"
            lid = f"L{i}" + ("m" if mi else "")

            def bn(part, base):
                return base if (_mir(part) != part or not mi) else base.replace(f"L{i}", f"L{i}m", 1)
            pids = []
            for h in range(len(pp) - 1):
                x, y = pp[h], pp[h + 1]
                face, lo, hi = adj[x][y]
                sb = bn(x, f"L{i}_o" if h == 0 else f"L{i}x{h}_o")
                db = bn(y, f"L{i}_i" if h == len(pp) - 2 else f"L{i}x{h + 1}_i")
                n = int(e["width"]) + 1
                L_ = max(n / PIN_DENS + 0.5, MIN_WIN)
                c = 0.5 * (lo + hi)
                pr = dict(id=f"{lid}_{h}", src=dict(part=x, bus=sb), dst=dict(part=y, bus=db), width=int(e["width"]),
                          kind=e["kind"], face=face, layers=list(FACE_LAYERS[face]),
                          window_um=[snap(c - L_ / 2), snap(c + L_ / 2)])
                if mi and face in "NS":
                    pr["order"] = "lsb_high"
                plan["ports"].append(pr)
                ports[pr["id"]] = pr
                pids.append(pr["id"])
                for part, bus, dr in ((x, sb, "out"), (y, db, "in")):
                    if (h == 0 and dr == "out") or (h == len(pp) - 2 and dr == "in"):
                        bl = T[P.parts[part]["type"]].setdefault("buses", [])
                        if not any(q["name"] == bus for q in bl):
                            bl.append(dict(name=bus, dir=dr, width=int(e["width"]), kind=e["kind"]))
            for h in range(1, len(pp) - 1):
                p = pp[h]
                nm = f"L{i}x{h}" if not (_mir(p) == p and mi) else f"L{i}mx{h}"
                sl = T[P.parts[p]["type"]].setdefault("ft_slots", [])
                if not any(q["name"] == nm for q in sl):
                    tf = {P.die_face(p, g): g for g in "NSEW"}      # die face -> type face (MY swaps E / W)
                    sl.append(dict(name=nm, in_face=tf[OPPF[adj[pp[h - 1]][p][0]]], out_face=tf[adj[p][pp[h + 1]][0]],
                                   width=int(e["width"]), stations=1))
            L = dict(id=lid, ports=pids, note=f"{pp[0]}->{pp[-1]} {e['kind']}" + (" (mirror)" if mi else "") +
                     " (B2n lane delta, HBM-BIND)")
            plan["lanes"].append(L)
            lanes[lid] = L
            added.append(f"{lid} {pp[0]}->{pp[-1]} {e['width']} b via {'/'.join(pp[1:-1]) or '-'}")
    # ---- every bundle (NW pair and its NE mirror) carries its RTL need
    P = S.Plan(plan)
    cap = defaultdict(int)
    for lid, L in P.lanes.items():
        p0, p1 = P.ports[L["ports"][0]], P.ports[L["ports"][-1]]
        cap[(p0["src"]["part"], p1["dst"]["part"], p0["kind"])] += int(p0["width"])
    short = []
    for bd in D["bundles"]:
        keys = [(bd["src"], bd["dst"], bd["kind"])]
        if len(bd["need"]) > 1:
            keys.append((_mir(bd["src"]), _mir(bd["dst"]), bd["kind"]))
        for k, nd in zip(keys, bd["need"]):
            if cap[k] < nd:
                short.append(f"{k[0]}->{k[1]} {k[2]} {cap[k]} < {nd}")
    log.append(f"lane delta ({Path(path).name}, {D['source']['file']} @ {D['source']['commit'].split()[0]}): "
               f"{len(rows)} lanes widened ({', '.join(rows)}); {len(added)} new lanes ({'; '.join(added)}); {len(D['bundles']) - len(short)}/{len(D['bundles'])} bundles carry their RTL need"
               + (f"; SHORT (hub perimeter / su-row cuts full, partition change needed): {'; '.join(short)}" if short else ""))
    return short


CORE_RESHAPE = HERE / "B2n_inputs" / "core_reshape.json"
FACE_COS = {(a, b): (1.0 if a == b else -1.0 if S.OPP[a] == b else 0.0) for a in "NSEW" for b in "NSEW"}


def _repin(pins, w, h, nw, nh):
    """re-place the pins on a new (smaller / reshaped) outline with cores_b2.place_pins: every port pulls toward its
    old face (cos 1), takes an adjacent face (cos 0) when that is full, the opposite face only within the
    core_faces mean rule (cores_b2.MEAN_MIN); per-face pin budget = the kit generator's (cores_b2 face_caps)."""
    import cores_b2 as CB
    ports = defaultdict(list)
    for p in pins:
        ports[CB.base(p["name"])].append(p)
    groups = []
    for port, ps in sorted(ports.items()):
        f = collections_most([CB.face_of(p["x"], p["y"], w, h) for p in ps])
        groups.append((port, [p["name"] for p in ps], f, {g: FACE_COS[(f, g)] for g in "NSEW"}))
    out, _ = CB.place_pins(groups, nw, nh)
    res = [dict(name=n, layer=ly, x=x, y=y) for n, ly, x, y in out]
    assert len(res) == len(pins)
    return res


def collections_most(xs):
    c = defaultdict(int)
    for x in xs:
        c[x] += 1
    return max(sorted(c), key=lambda k: c[k])


def reshape_outline(e, npins):
    """smallest outline (4.32 grid, aspect <= ASPECT) with (a) area - pin band >= macro area (with halo) + std / UTIL,
    (b) the largest macro + 2 pin bands inside, (c) the pins placeable at the kit face budget (place_pins)."""
    import cores_b2 as CB
    U = e.get("util", 0.5)
    band, halo = 12.96, 4.32
    mh = sum(n * (mw + 2 * halo) * (mh_ + 2 * halo) for n, mw, mh_ in e["macros"])
    need = mh + e["std_um2"] / U
    mw = max([m[1] for m in e["macros"]] or [0.0]) + 2 * band + 2 * halo
    mhh = max([m[2] for m in e["macros"]] or [0.0]) + 2 * band + 2 * halo
    best = None
    for i in range(10, 400):
        for j in range(10, 400):
            w, h = i * 4.32, j * 4.32
            if max(w, h) / min(w, h) > e.get("aspect", 1.5) + 1e-9:
                continue
            fits = (w >= mw and h >= mhh) or (h >= mw and w >= mhh)
            if not fits or w * h - band * 2 * (w + h) < need:
                continue
            if sum(CB.face_cap(f, w, h) for f in "NSEW") < npins * e.get("pin_slack", 1.05):
                continue
            key = (round(w * h, 2), abs(w - h), w)
            if best is None or key < best[0]:
                best = (key, (round(w, 4), round(h, 4)))
        if best and (i * 4.32) ** 2 / 1.5 > best[0][0]:
            break
    return best[1]


CORE_GROW = HERE / "B2n_inputs" / "core_grow.json"
OUTLINES = []
LAT = 8.64


def _regrow_pins(pins, w, h, nw, nh):
    """same pins on the same face in the same order (per layer), spread evenly on the plan tracks of the new outline
    (cores_b2.place_pins final rule)."""
    import cores_b2 as CB
    faces = defaultdict(list)
    for p in pins:
        f = CB.face_of(p["x"], p["y"], w, h)
        faces[(f, p["layer"])].append(p)
    out = []
    for (f, lay), ps in sorted(faces.items()):
        ps.sort(key=lambda p: (p["x"] if f in "NS" else p["y"]))
        L = nw if f in "NS" else nh
        second = lay in ("M6", "M7")
        tr = CB.tracks(L, f in "NS", lay if second else None)
        n = len(ps)
        if n > len(tr):
            raise ValueError(f"face {f} {lay}: {n} pins > {len(tr)} tracks on {nw}x{nh}")
        idx = [int(round(i * (len(tr) - 1) / max(1, n - 1))) if n > 1 else len(tr) // 2 for i in range(n)]
        for p, k in zip(ps, idx):
            a = tr[k]
            xy = dict(N=(a, round(nh - CB.INSET, 4)), S=(a, CB.INSET), E=(round(nw - CB.INSET, 4), a),
                      W=(CB.INSET, a))[f]
            out.append(dict(name=p["name"], layer=p["layer"], x=xy[0], y=xy[1]))
    assert len(out) == len(pins)
    return out


def core_grow(plan, log, out, path=CORE_GROW):
    """HBM-CORES outline grows (B2n_inputs/core_grow.json): every matching hard core gets its new outline, re-sited at
    the nearest free 8.64-lattice origin to its old centre (8.64 halo to other cores / soft leaves, inside the type),
    its pins_file re-written for the outline (_regrow_pins), its contents box / split bounding box and core clock tap
    re-derived, and every internal station landing on it (or with a register now on a core) re-routed by restation."""
    D = path if isinstance(path, dict) else json.loads(Path(path).read_text())
    T = plan["partition_types"]
    rows, fails = [], []

    def gm(g, mod):
        if "match" in g:
            return re.match(g["match"], mod) is not None
        return mod == g["module"] or (g.get("prefix") and mod.startswith(g["module"] + "__"))

    def ru(v):
        return round(math.ceil(v / 0.864 - 1e-9) * 0.864, 4)

    def ovl(a, b, m):
        return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m

    for g in D["grow"]:
        if "std_um2" in g and "outline" in g:
            g["_outline"] = tuple(g["outline"])
        if "std_um2" in g and "_outline" not in g:
            npin = max(len(json.loads((out / hc["pins_file"]).read_text())) for tn in g["types"]
                       for hc in T[tn]["hard_cores"] if gm(g, hc["module"]))
            g["_outline"] = reshape_outline(g, npin)
        for tn in g["types"]:
            t = T[tn]
            W, H = t["outline_um"]
            hcs = t["hard_cores"]
            match = [hc for hc in hcs if gm(g, hc["module"])]
            insts = {hc["inst"] for hc in hcs}

            def box(hc):
                dx, dy = hc.get("track_offset_um", [0.0, 0.0])
                x, y = hc["origin_um"][0] + dx, hc["origin_um"][1] + dy
                return (x, y, x + hc["outline_um"][0], y + hc["outline_um"][1])
            split = {c["inst"] for c in t.get("contents", []) if c["inst"] not in insts and
                     any(i.startswith(c["inst"] + "_") for i in insts)}
            soft = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                     c["origin_um"][1] + c["outline_um"][1], c["inst"]) for c in t.get("contents", [])
                    if "origin_um" in c and "outline_um" in c and c["inst"] not in insts and c["inst"] not in split]
            moved = {}

            def size(hc):
                ow, oh = hc["outline_um"]
                if "std_um2" in g:                 # reshape: one outline per module (max pin count of its views)
                    return g["_outline"]
                if "outline" in g:
                    return tuple(g["outline"])
                s_ = math.sqrt(g["area"])
                return ru(ow * s_), ru(oh * s_)
            sites, placed = {}, []
            for hc in sorted(match, key=lambda c_: c_["inst"]):      # 1. nearest free site to the old centre
                nw, nh = size(hc)
                ob = box(hc)
                dx, dy = hc.get("track_offset_um", [0.0, 0.0])
                cx, cy = (ob[0] + ob[2]) / 2, (ob[1] + ob[3]) / 2
                x0 = round((cx - nw / 2 - dx) / LAT) * LAT
                y0 = round((cy - nh / 2 - dy) / LAT) * LAT
                others = [box(o) for o in hcs if o is not hc and o["inst"] not in sites] + placed + \
                         [s_[:4] for s_ in soft]
                R_ = 80
                cands = sorted(((i, j) for i in range(-R_, R_ + 1) for j in range(-R_, R_ + 1)),
                               key=lambda ij: (abs(ij[0]) + abs(ij[1]), abs(ij[1]), ij))
                for i, j in cands:
                    ox, oy = x0 + i * LAT, y0 + j * LAT
                    nb = (ox + dx, oy + dy, ox + dx + nw, oy + dy + nh)
                    if nb[0] < LAT - 1e-6 or nb[1] < LAT - 1e-6 or nb[2] > W - LAT + 1e-6 or nb[3] > H - LAT + 1e-6:
                        continue
                    if any(ovl(nb, o, LAT - 1e-6) for o in others):
                        continue
                    sites[hc["inst"]] = (round(ox, 4), round(oy, 4))
                    placed.append(nb)
                    break
                else:
                    break
            if len(sites) < len(match):                               # 2. else re-pack the grown set as a grid
                sites = {}
                nw, nh = size(match[0])
                px, py = math.ceil((nw + LAT) / LAT - 1e-9) * LAT, math.ceil((nh + LAT) / LAT - 1e-9) * LAT
                ncol = int((W - 2 * LAT - nw) // px) + 1
                span = (ncol - 1) * px + nw
                gx = max(LAT, math.floor((W - span) / 2 / LAT) * LAT)
                gy = min(hc["origin_um"][1] for hc in match)
                order = sorted(match, key=lambda c_: (round(c_["origin_um"][1], 1), c_["origin_um"][0], c_["inst"]))
                rest = [box(o) for o in hcs if o not in match] + [s_[:4] for s_ in soft]
                for k, hc in enumerate(order):
                    ox, oy = gx + (k % ncol) * px, gy + (k // ncol) * py
                    nb = (ox, oy, ox + nw, oy + nh)
                    if nb[3] > H - LAT or any(ovl(nb, o, LAT - 1e-6) for o in rest):
                        fails.append(f"{tn}.{hc['inst']}: grid re-pack does not fit ({ncol} columns)")
                        sites = {}
                        break
                    sites[hc["inst"]] = (round(ox, 4), round(oy, 4))
                if sites:
                    rows.append(f"{tn}: grid re-pack {ncol} columns x {math.ceil(len(order) / ncol)} rows")
            for hc in sorted(match, key=lambda c_: c_["inst"]):
                if hc["inst"] not in sites:
                    fails.append(f"{tn}.{hc['inst']}: no free site")
                    continue
                ow, oh = hc["outline_um"]
                nw, nh = size(hc)
                ob = box(hc)
                best = sites[hc["inst"]]
                pins = json.loads((out / hc["pins_file"]).read_text())
                try:
                    npins = (_repin if g.get("repin") else _regrow_pins)(pins, ow, oh, nw, nh)
                except ValueError as e:
                    fails.append(f"{tn}.{hc['inst']}: {e}")
                    continue
                pf = f"cores/{hc['module']}__{nw:g}x{nh:g}__{tn}_{hc['inst']}.json"
                (out / pf).write_text(json.dumps(npins))
                old_pf = hc["pins_file"]
                hc.update(origin_um=list(best), outline_um=[nw, nh], pins_file=pf)
                hc["note"] = (hc.get("note", "").split(" | B2n grow")[0] +
                              f" | B2n grow (HBM-CORES): {ow:g}x{oh:g} -> {nw:g}x{nh:g}, was {old_pf.split('/')[-1]}")
                moved[hc["inst"]] = (ob, box(hc), {p["name"]: (p["x"], p["y"]) for p in npins})
                for c in t.get("contents", []):
                    if c["inst"] == hc["inst"] and "origin_um" in c:
                        c["origin_um"], c["outline_um"] = list(best), [nw, nh]
            if not moved:
                continue
            for c in t.get("contents", []):           # split masters: bounding box of their pieces
                if c["inst"] in split and "origin_um" in c:
                    bs = [box(o) for o in hcs if o["inst"].startswith(c["inst"] + "_")]
                    x0_, y0_ = min(b[0] for b in bs), min(b[1] for b in bs)
                    x1_, y1_ = max(b[2] for b in bs), max(b[3] for b in bs)
                    c["origin_um"] = [round(x0_, 4), round(y0_, 4)]
                    c["outline_um"] = [round(x1_ - x0_, 4), round(y1_ - y0_, 4)]

            def remap(pt):
                for ob, nb, _ in moved.values():
                    if ob[0] - 1.0 <= pt[0] <= ob[2] + 1.0 and ob[1] - 1.0 <= pt[1] <= ob[3] + 1.0:
                        fx = (pt[0] - ob[0]) / (ob[2] - ob[0])
                        fy = (pt[1] - ob[1]) / (ob[3] - ob[1])
                        return [round(nb[0] + min(max(fx, 0.0), 1.0) * (nb[2] - nb[0]), 3),
                                round(nb[1] + min(max(fy, 0.0), 1.0) * (nb[3] - nb[1]), 3)], True
                return pt, False
            nbox = [box(o) for o in hcs]
            nre = 0
            for e in t.get("internal_stations", []):
                e["from_um"], a1 = remap(e["from_um"])
                e["to_um"], a2 = remap(e["to_um"])
                on = any(b[0] < r[0] < b[2] and b[1] < r[1] < b[3] for r in e["regs_um"] for b in nbox)
                if a1 or a2 or on:
                    e["_regrow"] = True
                    nre += 1
            taps = t.get("clock", {}).get("taps", [])
            for tp in taps:
                ci, _, port = tp["name"].partition(".")
                if tp.get("kind") != "core" or ci not in moved:
                    continue
                ob, nb, pins = moved[ci]
                ck = [pins[port]] if port in pins else [xy for n_, xy in pins.items() if n_ in ("ck", "clk", "clock")]
                if ck:
                    x, y = nb[0] + ck[0][0], nb[1] + ck[0][1]
                else:
                    (x, y), _ = remap(tp["xy"])
                x, y = S.tap_clear(t, x, y, [tuple(o["xy"]) for o in taps if o is not tp], clear=4.32)
                tp["xy"] = [round(x, 4), round(y, 4)]
            rows.append(f"{tn}: {len(moved)} x {g['module']} -> {nw:g}x{nh:g} ({nre} internal links re-routed)")
    for g in D["grow"]:
        if "_outline" in g:
            o = [hc for tn in g["types"] for hc in T[tn]["hard_cores"] if gm(g, hc["module"])]
            nw, nh = g["_outline"]
            ow, oh = g["old"]
            halo = 4.32
            mh = sum(n * (a + 2 * halo) * (b + 2 * halo) for n, a, b in g["macros"])
            OUTLINES.append(dict(module=g.get("module", g.get("match")), views=[f"{tn}.{hc['inst']}" for tn in g["types"]
                                                            for hc in T[tn]["hard_cores"] if gm(g, hc["module"])],
                                 old_um=[ow, oh], new_um=[nw, nh], area_ratio=round(nw * nh / (ow * oh), 3),
                                 placed=[hc["inst"] for hc in o if list(hc["outline_um"]) == [nw, nh]],
                                 pins_files=[hc["pins_file"] for hc in o], macros=g["macros"], std_um2=g["std_um2"],
                                 std_fill_old=round(g["std_um2"] / (ow * oh - mh), 3),
                                 std_fill_new=round(g["std_um2"] / (nw * nh - mh), 3), why=g.get("why", "")))
    log.append(f"core outlines ({path.get('src', 'exp_lane.json') if isinstance(path, dict) else Path(path).name}): " + "; ".join(rows) +
               (f"; NOT FIT: {'; '.join(fails)}" if fails else ""))
    return fails


EXP_LANE = HERE / "B2n_inputs" / "exp_lane.json"


def exp_lane(plan, log, out, path=EXP_LANE):
    """GEOM 23:29 FAIL (30 pgslice_lg lane_exp* at 13-15% fill) + HBM-CORES2 23:30 request: every lane_exp view gets
    the 440.64 x 207.36 outline (core_grow, pins same face / order, _regrow_pins), ONE family macro placement (recorded
    in the core note and b2n_core_outlines.json) and ONE early core tap (kind core) beside its clock-pin cluster
    (all clock ports are die-clock roots: one entry, core-latency contract, I = measured mean)."""
    D = json.loads(Path(path).read_text())
    fails = core_grow(plan, log, out, D)
    g = D["grow"][0]
    T = plan["partition_types"]
    mp = "; ".join(f"k{m['k']} {m['origin_um'][0]:g},{m['origin_um'][1]:g} {m['orient']}" for m in D["macro_placement"])
    n = 0
    for tn in g["types"]:
        t = T[tn]
        taps = t["clock"].setdefault("taps", [])
        for hc in t["hard_cores"]:
            if not re.match(g["match"], hc["module"]) or list(hc["outline_um"]) != list(g["outline"]):
                continue
            pins = {q["name"]: q for q in json.loads((out / hc["pins_file"]).read_text())}
            ck = [pins[c] for c in D["clock_ports"] if c in pins]
            assert ck, f"{tn}.{hc['inst']}: no clock pin"
            ox, oy = hc["origin_um"]
            cx = sum(q["x"] for q in ck) / len(ck)
            cy = sum(q["y"] for q in ck) / len(ck)
            taps[:] = [tp for tp in taps if tp["name"].partition(".")[0] != hc["inst"]]
            x, y = S.tap_clear(t, ox + cx, oy + cy, [tuple(a["xy"]) for a in taps], clear=4.32)
            r = D["insertion"][f"{tn}.{hc['inst']}"]
            taps.append(dict(name=hc["inst"], kind="core", xy=[round(x, 4), round(y, 4)],
                             insertion_ps=round(max(float(r["mean_ps"]), 250.0), 3), budget_owner=hc["module"],
                             note=f"clock entry: {len(ck)} clock ports ({', '.join(sorted({c.split('[')[0] for c in D['clock_ports']}))}) "
                                  f"= one die-clock net, one pin cluster; HBM-ELEM measured I {r['mean_ps']} ps "
                                  f"(max {r['max_ps']}) on the 440.64x457.92 outline, view {r['view']}; re-measure after re-place"))
            t["clock"]["core_taps"] = "early"
            hc["note"] += (f" | family MACRO_PLACEMENT (B2n_inputs/exp_lane.json, 6 x {D['macro_placement'][0]['macro']},"
                           f" core frame): {mp} | reset entry rst_lane_n (clock cluster) + rst_n (S face), partition reset")
            n += 1
    for o in OUTLINES:
        if o["module"] == g["module"]:
            o.update(macro_placement=D["macro_placement"], clock_ports=D["clock_ports"], reset_ports=D["reset_ports"],
                     clock_entry="one early core tap per instance (plan clock.taps kind core, name = inst) beside the clock-pin cluster",
                     std_um2_range=[21300, 24900])
    log.append(f"exp lanes (GEOM 23:29, {Path(path).name}): {n} lane_exp cores -> {g['outline'][0]:g}x{g['outline'][1]:g}, "
               f"family macro placement ({len(D['macro_placement'])} SRAM), {n} early core taps")
    return fails


SU_GRID = HERE / "B2n_inputs" / "su_grid.json"


def su_grid(plan, log, path=SU_GRID):
    """COORD GEOM spot-check 10-24 23:23 (q_su00 tiles off-row, ~300 x 500 um holes): every listed type's hard cores
    re-placed on ONE regular grid (outline unchanged, pins_file unchanged).  The largest core class fills an R x C
    grid (R = rows that fit the height, row-major in the old (row, x) order, 8.64-lattice pitch = core + 8.64 halo);
    other hard cores and the soft leaves stack in one side column beside it.  Grid + column sit as one block at the x
    that minimises the width-weighted distance to the type's bus windows (spare area on the face away from the links).
    Moved items carry their core taps / internal station ends by translation; their stations are re-routed by
    restation; split bounding boxes re-derived."""
    D = json.loads(Path(path).read_text())
    P = S.Plan(plan)
    T = plan["partition_types"]
    rows = []
    for tn in D["types"]:
        t = T[tn]
        W, H = t["outline_um"]
        hcs = t["hard_cores"]
        insts = {h["inst"] for h in hcs}
        split = {c["inst"] for c in t["contents"] if c["inst"] not in insts and any(i.startswith(c["inst"] + "_")
                                                                                     for i in insts)}
        softs = [c for c in t["contents"] if "origin_um" in c and "outline_um" in c and c["inst"] not in insts
                 and c["inst"] not in split]
        cls = defaultdict(list)
        for h in hcs:
            cls[tuple(h["outline_um"])].append(h)
        multi = [k for k in cls if len(cls[k]) >= 2]   # grid cell = the largest repeated core (shorter ones stack)
        big = max(multi, key=lambda k: (k[0] * k[1], k)) if multi else max(cls, key=lambda k: (k[0] * k[1] * len(cls[k]), k))
        cw, ch = big
        # same-width shorter cores stack in one grid cell (exp lanes 207.36 x2 + 8.64 halo in a 457.92 cell)
        stk = {k: int((ch + LAT + 1e-6) // (math.ceil((k[1] + LAT) / LAT - 1e-9) * LAT)) for k in cls
               if k != big and abs(k[0] - cw) < 1e-6}
        stk = {k: v for k, v in stk.items() if v >= 2}

        def okey(h):
            return (round(h["origin_um"][1] / (ch / 2)), h["origin_um"][0], h["inst"])
        units = [[h] for h in cls[big]]
        for k, m in sorted(stk.items()):
            hs = sorted(cls[k], key=lambda h: h["inst"])
            hs = sorted(hs, key=lambda h: (int(re.sub(r"\D", "", h["inst"].rsplit("_", 1)[-1]) or 99), h["inst"]))
            units += [hs[i:i + m] for i in range(0, len(hs), m)]
        main = sorted(units, key=lambda u: okey(u[0]))
        side = sorted([h for k, v in cls.items() if k != big and k not in stk for h in v], key=lambda h: h["inst"]) + \
            sorted(softs, key=lambda c: (-c["outline_um"][1], c["inst"]))
        px = math.ceil((cw + LAT) / LAT - 1e-9) * LAT
        py = math.ceil((ch + LAT) / LAT - 1e-9) * LAT
        R = int((H - 2 * LAT - ch) // py) + 1
        C = math.ceil(len(main) / R)
        R = math.ceil(len(main) / C)                  # fewest rows for that column count (no empty row)
        gh = (R - 1) * py + ch
        y0 = max(LAT, math.floor((H - gh) / 2 / LAT) * LAT)
        # side column: shelf stack (two items side by side when both fit the column width)
        colw = max([math.ceil(o["outline_um"][0] / LAT - 1e-9) * LAT for o in side] or [0.0])
        pair = [o for o in side if o["outline_um"][0] * 2 + LAT <= colw + 1e-6]
        if pair and max(o["outline_um"][0] for o in pair) * 2 + LAT > colw:
            colw = max(colw, math.ceil((2 * max(o["outline_um"][0] for o in pair) + LAT) / LAT) * LAT)
        rel, y, x = {}, 0.0, 0.0
        rowh = 0.0
        for o in side:
            w_, h_ = o["outline_um"]
            if x > 0 and x + w_ <= colw + 1e-6:
                rel[o["inst"]] = (x, y)
                x += math.ceil((w_ + LAT) / LAT - 1e-9) * LAT
                rowh = max(rowh, h_)
                continue
            if x > 0:
                y += math.ceil((rowh + LAT) / LAT - 1e-9) * LAT
            rel[o["inst"]] = (0.0, y)
            x, rowh = math.ceil((w_ + LAT) / LAT - 1e-9) * LAT, h_
        sideh = y + rowh
        gw = (C - 1) * px + cw
        bw = gw + (colw + LAT if side else 0.0)
        assert sideh <= H - 2 * LAT and bw <= W - 2 * LAT, f"su_grid {tn}: block {bw:.0f}x{max(gh, sideh):.0f} does not fit"
        bt = CK._bus_targets(P, tn)
        wb = {b["name"]: int(b.get("width", 1)) for b in t.get("buses", [])}
        best = None
        for left in (False, True):                    # side column left or right of the grid
            for k in range(int((W - bw) // LAT) + 1):
                bx = k * LAT
                if bx < LAT or bx + bw > W - LAT:
                    continue
                cost = sum(wb.get(nm, 1) * max(bx - p[0], 0.0, p[0] - (bx + bw)) for nm, (_, p) in bt.items())
                key = (round(cost, 3), left, bx)
                if best is None or key < best[0]:
                    best = (key, left, bx)
        _, left, bx = best
        gx = bx + (colw + LAT if left and side else 0.0)
        sx = bx if left else bx + gw + LAT
        new = {}
        for i, u in enumerate(main):
            r, c = divmod(i, C)
            yy = y0 + r * py
            for h in u:
                new[h["inst"]] = (round(gx + c * px, 4), round(yy, 4))
                yy += math.ceil((h["outline_um"][1] + LAT) / LAT - 1e-9) * LAT
        sy = max(LAT, math.floor((H - sideh) / 2 / LAT) * LAT)
        for o in side:
            new[o["inst"]] = (round(sx + rel[o["inst"]][0], 4), round(sy + rel[o["inst"]][1], 4))
        # apply: translation per item
        delta, oldb = {}, {}
        for o in hcs + softs:
            ox, oy = o["origin_um"]
            nx, ny = new[o["inst"]]
            dx_, dy_ = (o.get("track_offset_um") or [0.0, 0.0]) if o in hcs else (0.0, 0.0)
            oldb[o["inst"]] = (ox + dx_, oy + dy_, ox + dx_ + o["outline_um"][0], oy + dy_ + o["outline_um"][1])
            delta[o["inst"]] = (nx - ox, ny - oy)
            o["origin_um"] = [nx, ny]
        for c in t["contents"]:
            if c["inst"] in insts and "origin_um" in c:
                c["origin_um"] = list(new[c["inst"]])
            if c["inst"] in split and "origin_um" in c:
                bs = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
                       h["origin_um"][1] + h["outline_um"][1]) for h in hcs if h["inst"].startswith(c["inst"] + "_")]
                x0_, y0_ = min(b[0] for b in bs), min(b[1] for b in bs)
                c["origin_um"] = [round(x0_, 4), round(y0_, 4)]
                c["outline_um"] = [round(max(b[2] for b in bs) - x0_, 4), round(max(b[3] for b in bs) - y0_, 4)]

        def move(pt):
            for n_, b in oldb.items():
                if b[0] - 1.0 <= pt[0] <= b[2] + 1.0 and b[1] - 1.0 <= pt[1] <= b[3] + 1.0:
                    return [round(pt[0] + delta[n_][0], 3), round(pt[1] + delta[n_][1], 3)], True
            return pt, False
        nre = 0
        for e in t.get("internal_stations", []):
            e["from_um"], a1 = move(e["from_um"])
            e["to_um"], a2 = move(e["to_um"])
            e["_regrow"] = True                       # every register re-routed around the new core grid
            nre += 1
        taps = t.get("clock", {}).get("taps", [])
        for tp in taps:
            ci = tp["name"].partition(".")[0]
            if tp.get("kind") == "core" and ci in delta:
                x, y = tp["xy"][0] + delta[ci][0], tp["xy"][1] + delta[ci][1]
                x, y = S.tap_clear(t, x, y, [tuple(o["xy"]) for o in taps if o is not tp], clear=4.32)
                tp["xy"] = [round(x, 4), round(y, 4)]
        if "tap_um" in t.get("clock", {}):
            t["clock"]["tap_um"] = [round(v, 4) for v in S.tap_clear(t, *t["clock"]["tap_um"], clear=4.32)]
        rows.append(f"{tn} {R}x{C} grid of {len(main)} {cw:g}x{ch:g} cells ({sum(len(u) for u in main)} cores, "
                    f"{sum(len(u) > 1 for u in main)} stacked) + side column {len(side)} "
                    f"({'W' if left else 'E'} of grid) at x {bx:g}..{bx + bw:g} of {W:g} ({nre} internal links re-routed)")
    log.append("SU grid (COORD GEOM 23:23, B2n_inputs/su_grid.json): " + "; ".join(rows))


def drop_die_layers(plan, log):
    n = 0
    for t in plan["partition_types"].values():
        for f, ls in list(t.get("face_layers", {}).items()):
            t["face_layers"][f] = [x for x in ls if x not in DIE_ONLY]
    for p in plan["ports"]:
        if any(x in DIE_ONLY for x in p.get("layers", [])):
            p["layers"] = [x for x in p["layers"] if x not in DIE_ONLY]
            n += 1
    lb = plan["die"]["layer_budget"]
    lb["die_use"] = [u for u in lb.get("die_use", []) if u != "ft_reserved"] + ["reset"]
    plan["die"]["reach_um"] = REACH
    plan["budgets"]["ft_station_max_um"] = REACH
    log.append(f"decision 12: {n} ports drop M8/M9 (2 pin layers), reach / ft_station_max 405")


def _pava(items):
    """items: [(desired_start, length, lo, hi)] in order; lo/hi bound the START.  Least-squares shift keeping order and
    GAP between windows; returns starts.  Pool-adjacent-violators over blocks, each block clipped to its bounds."""
    blocks = []      # [sum_desired_offsetted, n, members, lo, hi, offsets]
    for i, (d, L, lo, hi) in enumerate(items):
        blocks.append(dict(m=[i], off=[0.0], s=d, n=1, lo=lo, hi=hi, len=L))
        while True:
            b = blocks[-1]
            pos = min(max(b["s"] / b["n"], b["lo"]), b["hi"])
            b["pos"] = pos
            if len(blocks) < 2:
                break
            a = blocks[-2]
            if a["pos"] + a["len"] + GAP <= pos + 1e-9:
                break
            # merge b into a: b's members sit after a's
            sh = a["len"] + GAP
            a["m"] += b["m"]
            a["off"] += [o + sh for o in b["off"]]
            a["s"] += b["s"] - sh * b["n"]
            a["n"] += b["n"]
            a["lo"] = max(a["lo"], b["lo"] - sh)
            a["hi"] = min(a["hi"], b["hi"] - sh)
            a["len"] += GAP + b["len"]
            blocks.pop()
            a["pos"] = min(max(a["s"] / a["n"], a["lo"]), a["hi"])
            blocks[-1] = a
    out = [None] * len(items)
    bad = []
    for b in blocks:
        if b["lo"] > b["hi"] + 1e-6:
            bad.append(b["m"])
        for i, o in zip(b["m"], b["off"]):
            out[i] = b["pos"] + o
    return out, bad


def rewindow(plan, log, fixed_ids=frozenset()):
    P = S.Plan(plan)
    ports = {p["id"]: p for p in plan["ports"]}
    groups = defaultdict(list)
    for pid, p in ports.items():
        part = P.face_part(pid)
        line, a, b = CK.face_line(P.rect(part), p["face"])
        fixed = S.DIE_PART in (p["src"]["part"], p["dst"]["part"]) or pid in fixed_ids
        if not fixed:
            _, a2, b2 = CK.face_line(P.rect(p["dst"]["part"]), S.OPP[p["face"]])
            a, b = max(a, a2), min(b, b2)
        axis = "H" if p["face"] in "NS" else "V"
        groups[(axis, round(line, 3))].append((pid, a, b, fixed))
    grown = moved = 0
    worst = []
    for key, mem in groups.items():
        rows = []
        for pid, a, b, fixed in mem:
            lo, hi = sorted(ports[pid]["window_um"])
            need = max(S.port_pins_count(ports[pid]) / PIN_DENS + 0.5, MIN_WIN)
            L = (hi - lo) if fixed else max(hi - lo, need)
            c = 0.5 * (lo + hi)
            d = c - L / 2
            if fixed:
                blo = bhi = lo
            else:
                blo, bhi = a + 0.5, b - 0.5 - L
            rows.append((c, pid, d, L, blo, bhi, lo, hi))
        rows.sort()
        starts, bad = _pava([(d, L, blo, bhi) for _, _, d, L, blo, bhi, _, _ in rows])
        for idx in bad:
            worst.append([rows[i][1] for i in idx][:4])
        for (c, pid, d, L, blo, bhi, lo, hi), s0 in zip(rows, starts):
            nw = [snap(s0), snap(s0 + L)] if not fixed else [lo, hi]
            if abs(nw[0] - lo) > 1e-4 or abs(nw[1] - hi) > 1e-4:
                moved += 1
                grown += (L > hi - lo + 1e-6)
                ports[pid]["window_um"] = nw
    log.append(f"re-windowed {moved} ports ({grown} grown to <= {PIN_DENS:g} pins/um on 2 layers); "
               f"{len(worst)} infeasible face groups")
    return worst


def enforce_mirror(plan, log):
    """replicated types (2 instances): the second instance's ports take the first instance's windows through the type
    frame, so both carry ONE pin table (check: 'a replicated type must have identical pins')."""
    P = S.Plan(plan)
    ports = {p["id"]: p for p in plan["ports"]}
    end = {}
    for pid, p in ports.items():
        for sd in ("src", "dst"):
            end[(p[sd]["part"], p[sd]["bus"], sd)] = pid
    insts = defaultdict(list)
    for n, p in P.parts.items():
        insts[p["type"]].append(n)
    touched, n = set(), 0
    pairs = []
    for tn, ps in insts.items():
        if len(ps) != 2:
            continue
        A, B = sorted(ps, key=lambda q: (P.orient(q) != "R0", P.parts[q]["origin_um"][0]))
        for (part, bus, sd), pid in list(end.items()):
            if part != A:
                continue
            qid = end.get((B, bus, sd))
            if not qid:
                continue
            p, q = ports[pid], ports[qid]
            if p["face"] in "NS":
                pts = [(c, 0.0) for c in p["window_um"]]
                nw = sorted(P.to_die(B, P.to_type(A, xy))[0] for xy in pts)
            else:
                pts = [(0.0, c) for c in p["window_um"]]
                nw = sorted(P.to_die(B, P.to_type(A, xy))[1] for xy in pts)
            nw = [snap(v) for v in nw]
            if nw != sorted(q["window_um"]):
                q["window_um"] = nw
                n += 1
            touched |= {pid, qid}
            pairs.append((A, B, pid, qid))
    log.append(f"mirror: {n} second-instance port windows set from the first instance (type frame)")
    return touched, pairs


def _tab(P, part, pid):
    ax = 0 if P.ports[pid]["face"] in "NS" else 1
    out = []
    for bit, ln, c in P.port_pins(pid):
        xy = (c, 0.0) if ax == 0 else (0.0, c)
        out.append((bit, ln, round(P.to_type(part, xy)[ax], 4)))
    return sorted(out)


def fix_mirror_pins(plan, pairs, log):
    """the nearest-track pick is mirror-equivariant only for an odd usable-track count when the pin count is odd
    (schema.spread): nudge the first instance's window end by 0.008-um steps (mirrored on the second) until both
    instances get one pin table."""
    ports = {p["id"]: p for p in plan["ports"]}
    fixed = bad = 0
    for A, B, pid, qid in pairs:
        P = S.Plan(plan)
        if _tab(P, A, pid) == _tab(P, B, qid):
            continue
        p, q = ports[pid], ports[qid]
        lo0, hi0 = sorted(p["window_um"])
        ok = False
        for k in list(range(1, 40)) + list(range(-1, -40, -1)):
            p["window_um"] = [lo0, snap(hi0 + k * SNAP)]
            ax = 0 if p["face"] in "NS" else 1
            pts = [((c, 0.0) if ax == 0 else (0.0, c)) for c in p["window_um"]]
            q["window_um"] = sorted(snap(P.to_die(B, P.to_type(A, xy))[ax]) for xy in pts)
            P = S.Plan(plan)
            try:
                if _tab(P, A, pid) == _tab(P, B, qid):
                    ok = True
                    break
            except ValueError:
                continue
        if ok:
            fixed += 1
        else:
            bad += 1
            p["window_um"] = [lo0, hi0]
    log.append(f"mirror pin tables: {fixed} port pairs nudged to one table, {bad} unresolved")


def reset_wavefront(plan, log):
    """OWNER DECISION 13: whole-die root + neighbour wavefront (reset_tree.py release=wavefront, lane RESET).  Hard
    types (prebuilt: q_sm*, PHY_N) take their reset pin on the face toward a soft neighbour's rst_o site: the face
    point within MARGIN of a site for every instance, nearest the face midpoint (their own reset fan-out stays inside the
    hard view, reset.depth)."""
    import reset_tree as RT
    if not hasattr(RT, "wf_solve"):
        log.append("reset: wavefront mode not in this tool base (RESET claude/reset-1024 pending) -> B2m reset kept")
        return
    plan["reset"]["release"] = "wavefront"
    P = S.Plan(plan)
    hard = {n for n in P.parts if P.types[P.parts[n]["type"]].get("hard")}
    sites = [P.to_die(q, s_["xy"]) for q in P.parts if q not in hard for s_ in RT.face_sites(P, P.parts[q]["type"])]
    hp = RT.hop_um(P) - RT.MARGIN_UM
    moved = []
    for tn in sorted({P.parts[n]["type"] for n in hard}):
        insts = [n for n in hard if P.parts[n]["type"] == tn]
        t = plan["partition_types"][tn]

        def dist(c):
            return max(min(abs(x - X) + abs(y - Y) for x, y in sites) for X, Y in (P.to_die(n, c) for n in insts))
        cur = tuple(t["reset"]["tap_um"])
        if dist(cur) <= hp:
            continue
        w, h = t["outline_um"]
        st = 8.64
        cands = [(k * st, y) for k in range(int(w // st) + 1) for y in (4.32, h - 4.32)] + \
                [(x, k * st) for k in range(int(h // st) + 1) for x in (4.32, w - 4.32)]
        ok = [c for c in cands if dist(c) <= 100.0] or [min(cands, key=dist)]

        def mid_off(c):
            if c[1] in (4.32, h - 4.32):
                return abs(c[0] - w / 2)
            return abs(c[1] - h / 2)
        c = min(ok, key=lambda c_: (mid_off(c_), dist(c_)))
        t["reset"]["tap_um"] = [round(c[0], 3), round(c[1], 3)]
        moved.append(f"{tn} {list(cur)} -> {t['reset']['tap_um']} ({dist(c):.0f} um to a soft rst_o site)")
    log.append("reset: release = wavefront (decision 13); hard reset pins moved to a face: " + "; ".join(moved))


def _type_routes(P):
    """{(type, slot): type-frame route polyline} from the first lane crossing of each slot."""
    out = {}
    for lid in P.lanes:
        for part, slot, a, b in P.lane_crossings(lid):
            if not slot:
                continue
            key = (P.parts[part]["type"], slot)
            if key in out:
                continue
            s = P.slot(part, slot) or {}
            seg = CK.zroute(P.port_point(a), P.port_point(b), P.die_face(part, s.get("in_face", "W")),
                            P.die_face(part, s.get("out_face", "E")))
            out[key] = [P.to_type(part, q) for q in seg]
    return out


def _boxes(t):
    bx = []
    for hc in t.get("hard_cores", []):
        dx, dy = hc.get("track_offset_um", [0.0, 0.0])
        bx.append((hc["origin_um"][0] + dx, hc["origin_um"][1] + dy, hc["outline_um"][0], hc["outline_um"][1]))
    return bx


def _chain(router, free, a, b):
    """stations from a (incl. a near-face site) to b with every hop <= HOP; off the cores."""
    first = free(a)
    regs = [first] + router(first, b)
    return regs


def restation(plan, log):
    P = S.Plan(plan)
    routes = _type_routes(P)
    tot0 = tot1 = 0
    ist0 = ist1 = added = 0
    fails = []
    for tn, t in plan["partition_types"].items():
        w, h = t["outline_um"]
        boxes = _boxes(t)
        router = RelayRouter(boxes, w, h, HOP)
        router_reach = RelayRouter(boxes, w, h, REACH - 1.0)
        free = (lambda p, boxes=boxes, w=w, h=h: free_point(p, boxes, w, h))
        for sl in t.get("ft_slots", []):
            seg = routes.get((tn, sl["name"]))
            if not seg:
                continue
            tot0 += int(sl.get("stations", 1))
            try:
                regs = _chain(router, free, seg[0], seg[-1])
            except ValueError as e:
                fails.append(f"{tn}.{sl['name']}: {e}")
                continue
            # spacing rule (check R3): route length / stations <= 405
            L = CK.plen(seg)
            while L / len(regs) > REACH:
                regs.append(regs[-1])
            sl["stations"] = len(regs)
            sl["regs_um"] = [[round(v, 3) for v in p] for p in regs]
            sl.pop("bit_sites_um", None)
            tot1 += len(regs)
        ist = t.get("internal_stations", [])
        for e in ist:
            ist0 += len(e["regs_um"])
            if not e.pop("_regrow", False) and CK._hops_ok(e["from_um"], e["regs_um"], e["to_um"], REACH):
                ist1 += len(e["regs_um"])
                continue
            a_, b_ = tuple(e["from_um"]), tuple(e["to_um"])
            land = free(b_)            # the station next to the capture pin, off the core (keeps the pin face)
            regs = None
            for r_ in (router, router_reach):
                try:
                    regs = r_(a_, land)
                    break
                except ValueError as ex:
                    err = ex
            if regs is None:
                fails.append(f"{tn} internal {e.get('conn')}: {err}")
                continue
            if not regs or abs(regs[-1][0] - land[0]) + abs(regs[-1][1] - land[1]) > 1.0:
                regs = list(regs) + [land]
            if not CK._hops_ok(a_, regs, b_, REACH):
                fails.append(f"{tn} internal {e.get('conn')}: hop > {REACH:g} um after re-stationing")
            e["regs_um"] = [[round(v, 3) for v in p] for p in regs]
            e["note"] = (e.get("note", "").split(" | B2n")[0] + f" | B2n decision 12: {len(regs)} station(s), "
                         f"hops <= {REACH:g} um")
            ist1 += len(regs)
    # new internal links now over 405 um (were <= 750/900): same enumeration as check_completeness
    P = S.Plan(plan)
    for tn, t in plan["partition_types"].items():
        if t.get("hard"):
            continue
        w, h = t["outline_um"]
        boxes = _boxes(t)
        bxs = {}
        for hc in t.get("hard_cores", []):
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            x0, y0 = hc["origin_um"][0] + dx, hc["origin_um"][1] + dy
            bxs[hc["inst"]] = (x0, y0, x0 + hc["outline_um"][0], y0 + hc["outline_um"][1])
        for c in t.get("contents", []):
            if c["inst"] not in bxs and "origin_um" in c and "outline_um" in c:
                x0, y0 = c["origin_um"]
                bxs[c["inst"]] = (x0, y0, x0 + c["outline_um"][0], y0 + c["outline_um"][1])
        if not bxs:
            continue
        router = RelayRouter(boxes, w, h, HOP)
        free = (lambda p, boxes=boxes, w=w, h=h: free_point(p, boxes, w, h))
        ist = t.setdefault("internal_stations", [])
        conns = {e.get("conn") for e in ist if e.get("conn")}

        def covered(key, a, b_box):
            if key in conns:
                return True
            return any(abs(e["from_um"][0] - a[0]) + abs(e["from_um"][1] - a[1]) <= 50.0
                       and CK._box_dist(e["to_um"], b_box) <= 50.0 for e in ist)

        def near(a, box):
            return (min(max(a[0], box[0]), box[2]), min(max(a[1], box[1]), box[3]))

        bt = None
        for b in t.get("buses", []):
            lf = b.get("leaf") or ""
            li = lf.split(".")[0]
            cand = [ci for ci in bxs if ci == li or ci.startswith(li + "_")] if li else []
            if not cand:
                continue
            if bt is None:
                bt = CK._bus_targets(P, tn)
            if b["name"] not in bt:
                continue
            a = bt[b["name"]][1]
            ci = min(cand, key=lambda c_: CK._box_dist(a, bxs[c_]))
            d = CK._box_dist(a, bxs[ci])
            if d > REACH and not covered(f"bus:{b['name']}", a, bxs[cand[0]]) and not covered(lf, a, bxs[cand[0]]):
                tgt = near(a, bxs[ci])
                try:
                    regs = router(a, tgt) or [free(a)]
                except ValueError as ex:
                    fails.append(f"{tn} bus {b['name']}: {ex}")
                    continue
                if not CK._hops_ok(a, regs, tgt, REACH):
                    regs = regs + [free(tgt)]
                ist.append(dict(conn=f"bus:{b['name']}", from_um=[round(a[0], 3), round(a[1], 3)],
                                to_um=[round(tgt[0], 3), round(tgt[1], 3)],
                                regs_um=[[round(v, 3) for v in p] for p in regs], bits=int(b.get("width", 1)),
                                launch=f"face bus {b['name']}", capture=lf,
                                note=f"B2n decision 12: face window -> {lf} {d:.0f} um, {len(regs)} station(s), "
                                     f"hops <= {REACH:g} um"))
                conns.add(f"bus:{b['name']}")
                added += 1
        nets = defaultdict(set)
        for c in t.get("contents", []):
            for lp, v in c.get("bind", {}).items():
                if v.startswith("net:"):
                    nets[v[4:]].add(c["inst"])
        for nm, insts in nets.items():
            ins = sorted(i for i in insts if i in bxs)
            for i, x in enumerate(ins):
                for y in ins[i + 1:]:
                    bx, by = bxs[x], bxs[y]
                    d = max(bx[0] - by[2], by[0] - bx[2], 0) + max(bx[1] - by[3], by[1] - bx[3], 0)
                    if d <= REACH or f"{x}|{y}" in conns or f"{y}|{x}" in conns:
                        continue
                    cy = ((by[0] + by[2]) / 2, (by[1] + by[3]) / 2)
                    a = near(cy, bx)
                    tgt = near(a, by)
                    try:
                        regs = router(a, tgt) or [free(a)]
                    except ValueError as ex:
                        fails.append(f"{tn} net {nm} {x}|{y}: {ex}")
                        continue
                    if not CK._hops_ok(a, regs, tgt, REACH):
                        regs = regs + [free(tgt)]
                    ist.append(dict(conn=f"{x}|{y}", from_um=[round(a[0], 3), round(a[1], 3)],
                                    to_um=[round(tgt[0], 3), round(tgt[1], 3)],
                                    regs_um=[[round(v, 3) for v in p] for p in regs], bits=1, launch=x, capture=y,
                                    note=f"B2n decision 12: net {nm} {d:.0f} um core link, {len(regs)} station(s), "
                                         f"hops <= {REACH:g} um"))
                    conns.add(f"{x}|{y}")
                    added += 1
        if not ist:
            t.pop("internal_stations", None)
    log.append(f"ft slot stations {tot0} -> {tot1}; internal stations {ist0} -> {ist1} (+{added} new links over "
               f"{REACH:g} um); {len(fails)} unroutable")
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(HERE / "B2m"))
    ap.add_argument("--out", default=str(HERE / "B2n"))
    a = ap.parse_args(argv)
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in SIDECARS:
        s, d = src / f, out / f
        if s.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(s, d)
        elif s.exists():
            shutil.copy2(s, d)
    plan = json.loads((src / "die_plan.json").read_text())
    log = []
    plan["die"]["name"] = "hbm_arch_B2n"
    plan["die"]["label"] = plan["die"]["label"].replace("B2m = ", "B2n = B2m + decision 12 (ft <= M7, 405-um "
                                                        "stations); B2m = ")
    drop_die_layers(plan, log)
    move_boundaries(plan, log)
    short = lane_delta(plan, log)
    rewindow(plan, log)
    touched, pairs = enforce_mirror(plan, log)
    worst = rewindow(plan, log, fixed_ids=touched)
    fix_mirror_pins(plan, pairs, log)
    grow_fail = core_grow(plan, log, out, CORE_RESHAPE) + core_grow(plan, log, out) + exp_lane(plan, log, out)
    su_grid(plan, log)
    fails = restation(plan, log)
    import b2m as B2M   # noqa: E402  (H-tree + tap assignment re-derived: su10/su30 / spu0/spu1 rects moved)
    B2M.clock(plan, out, log)
    nft = 0
    for t in plan["partition_types"].values():      # ruling 9.3: no ft reservation on M8/M9 (H-tree NDR is clock)
        fb = t.get("ft_budget")
        if fb is not None:
            for ln in DIE_ONLY:
                nft += fb.pop(ln, None) is not None
            if not fb:
                t.pop("ft_budget")
    log.append(f"ft_budget: {nft} M8/M9 ft reservations dropped (ruling 9.3)")
    reset_wavefront(plan, log)
    P = S.Plan(plan)
    plan["latency"]["lanes"] = {lid: P.lane_latency(lid) for lid in P.lanes}
    c0 = json.loads((src / "die_plan.json").read_text())["latency"]["lanes"]
    dc = {lid: plan["latency"]["lanes"][lid]["cycles"] - c0[lid]["cycles"] for lid in c0 if lid in plan["latency"]["lanes"]}
    up = [v for v in dc.values() if v > 0]
    log.append(f"latency: {len(up)}/{len(dc)} lanes +cycles (max +{max(up) if up else 0}, sum +{sum(up)})")
    plan["note"] = plan.get("note", "") + " | B2n derived by physical/die_plan/hbm_arch/b2n.py: " + "; ".join(log)
    (out / "die_plan.json").write_text(json.dumps(plan, indent=0) + "\n")
    (out / "die_io.json").write_text((src / "die_io.json").read_text())
    (out / "b2n_report.json").write_text(json.dumps(dict(log=log, infeasible_faces=worst, unroutable=fails,
                                                         lane_delta_short=short, core_grow_unfit=grow_fail,
                                                         lane_cycle_delta={k: v for k, v in dc.items() if v}),
                                                    indent=1) + "\n")
    lc = dict(schema="opentallas.hbm_b2n_lane_cycles.v1", plan="physical/die_plan/hbm_arch/B2n (claude/hbm-b2n-1024)",
              rule="decision 12 / rulings 9.3+9.4 + HBM-BIND lane delta (B2n_inputs/lane_delta.json)",
              summary=dict(lanes=len(dc), lanes_added=len(up), max_added=max(up) if up else 0, sum_added=sum(up),
                           new_lanes=sorted(set(plan["latency"]["lanes"]) - set(c0)), lane_delta_short=short),
              lanes={lid: dict(b2m=c0[lid]["cycles"] if lid in c0 else None, b2n=v["cycles"],
                               added=(v["cycles"] - c0[lid]["cycles"]) if lid in c0 else None,
                               note=P.lanes[lid].get("note", ""))
                     for lid, v in sorted(plan["latency"]["lanes"].items(),
                                          key=lambda kv: (int(kv[0][1:].rstrip("m")), kv[0]))})
    src_t = json.loads((src / "die_plan.json").read_text())["partition_types"]
    lc["types_changed"] = {tn: sorted(k for k in set(t) | set(src_t.get(tn, {})) if t.get(k) != src_t.get(tn, {}).get(k))
                           for tn, t in sorted(plan["partition_types"].items()) if t != src_t.get(tn)}
    if OUTLINES and out.resolve() == (HERE / "B2n").resolve():
        (ROOT / "results/arch/hbm_arch_1024/b2n_core_outlines.json").write_text(json.dumps(dict(
            schema="opentallas.hbm_b2n.core_outlines.v1", plan="physical/die_plan/hbm_arch/B2n (claude/hbm-b2n-1024)",
            source="B2n_inputs/core_reshape.json (HBM-ELEM GEOM placed2 low-fill FAILs, c6d07a7a0e)",
            rule=reshape_outline.__doc__.strip() + " | " + _repin.__doc__.strip(), cores=OUTLINES), indent=1) + "\n")
    rp = ROOT / "results/arch/hbm_arch_1024/b2n_lane_cycles.json"
    if out.resolve() == (HERE / "B2n").resolve():
        rp.write_text(json.dumps(lc, indent=1) + "\n")
    print("\n".join(log))
    for x in (worst[:5] + fails[:10]):
        print("  !", x)


if __name__ == "__main__":
    main()
