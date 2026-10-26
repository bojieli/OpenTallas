#!/usr/bin/env python3
"""GEOM-REVIEW die-level review pack (independent second review, owner order 2026-10-24 08:05).

Complements tools/die_plan/render.py (G1 render) with the pictures and numbers a floorplan reviewer asks for:

    python3 tools/geom_review/plan_review.py PLAN.json OUTDIR [--tools DIR] [--g0 g0_report.json]

Uses the plan's own tools/die_plan (pass --tools to pick the branch's copy).  Writes into OUTDIR:
  die_cores.png      whole die: partitions by type, hard cores (ROM / SRAM / split macros) filled, die IO, taps, root
  die_wire.png       lane bit-density heat map (bits x um routed per 100x100 um bin) + lanes coloured by bit-um
  zoom_*.png         auto-chosen zooms: densest bundle bin, longest lane, worst seam (pins/um), clock root, IO edge,
                     the partition with the most hard-core area, the thinnest partition
  review.json        metrics: lane wire cost ranking, hop/reach, order flips (twists) along lanes, per-seam pin density,
                     clock root->tap distances + neighbour tap distance across seams, aspect ratios, slivers,
                     hard-core fill and halos, types/instances/orients, die IO edge distance, uncovered die area
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def load(tools, plan_path):
    sys.path.insert(0, str(Path(tools).resolve()))
    import schema as S
    import check as C
    raw = S.load(plan_path)
    P = S.Plan(raw, path=plan_path)
    geo = {lid: C.lane_geometry(P, lid) for lid in P.lanes}
    return S, C, raw, P, geo


def plen(pts):
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))


def lane_width(P, lid):
    return P.ports[P.lanes[lid]["ports"][0]]["width"]


def seams(P):
    """shared faces between abutting partitions: {(a,b,face_of_a): dict(len, ports, bits, lo, hi, axis, at)}"""
    out = {}
    for pid, pr in P.ports.items():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if "@die" in (a, b):
            continue
        key = tuple(sorted((a, b)))
        ra, rb = P.rect(a), P.rect(b)
        f = pr["face"]
        s = out.setdefault(key, dict(ports=0, bits=0, face=f, a=a, b=b))
        s["ports"] += 1
        s["bits"] += pr["width"]
        if f in "EW":
            lo, hi = max(ra[1], rb[1]), min(ra[3], rb[3])
            s["axis"], s["at"] = "x", (ra[2] if f == "E" else ra[0])
        else:
            lo, hi = max(ra[0], rb[0]), min(ra[2], rb[2])
            s["axis"], s["at"] = "y", (ra[3] if f == "N" else ra[1])
        s["lo"], s["hi"] = lo, hi
        s["len"] = max(hi - lo, 1e-3)
    for s in out.values():
        s["bits_per_um"] = round(s["bits"] / s["len"], 3)
    return out


def ccw(r, face, c):
    """CCW perimeter coordinate of a face point (c = coordinate along the face) on rect r."""
    x0, y0, x1, y1 = r
    w, h = x1 - x0, y1 - y0
    return {"S": c - x0, "E": w + (c - y0), "N": w + h + (x1 - c), "W": 2 * w + h + (y1 - c)}[face]


def inversions(seq):
    """number of inversions (merge sort)."""
    def ms(a):
        if len(a) <= 1:
            return a, 0
        m = len(a) // 2
        l, x = ms(a[:m])
        r, y = ms(a[m:])
        out, i, j, k = [], 0, 0, x + y
        while i < len(l) and j < len(r):
            if l[i] <= r[j]:
                out.append(l[i]); i += 1
            else:
                out.append(r[j]); j += 1; k += len(l) - i
        out += l[i:] + r[j:]
        return out, k
    return ms(list(seq))[1]


def twists(P):
    """per (partition, ft slot) crossing: are the in-face and out-face pins wireable without crossings inside the
    partition?  Planar chords between two disjoint boundary arcs are crossing-free iff the CCW bit order on one arc is
    the reverse of the CCW bit order on the other.  frac = inversions / max inversions (0 = clean, 1 = full twist)."""
    from schema import OPP
    res = {}
    for lid in P.lanes:
        for part, slot, a, b in P.lane_crossings(lid):
            key = (part, slot)
            if key in res or part == "@die":
                continue
            r = P.rect(part)
            fa = OPP[P.ports[a]["face"]] if P.ports[a]["src"]["part"] != "@die" else P.ports[a]["face"]
            fb = P.ports[b]["face"]
            if P.ports[b]["src"]["part"] == "@die":
                continue
            pa = {}
            for bit, ln, c in P.port_pins(a):
                pa.setdefault(bit, ccw(r, fa, c))
            pb = {}
            for bit, ln, c in P.port_pins(b):
                pb.setdefault(bit, ccw(r, fb, c))
            bits = sorted(set(pa) & set(pb))
            ca = [c for _, _, c in P.port_pins(a)]
            cb = [c for _, _, c in P.port_pins(b)]
            ov = max(0.0, min(max(ca), max(cb)) - max(min(ca), min(cb))) if fa in "EW" and fb in "EW" or \
                fa in "NS" and fb in "NS" else 0.0
            n = len(bits)
            if n < 2:
                continue
            ia = sorted(bits, key=lambda q: pa[q])
            ob = sorted(bits, key=lambda q: -pb[q])
            rank = {q: i for i, q in enumerate(ob)}
            inv = inversions([rank[q] for q in ia])
            res[key] = dict(part=part, type=P.parts[part]["type"], slot=slot, lane=lid, bits=n, faces=fa + fb,
                            kind="uturn" if fa == fb else ("straight" if OPP[fa] == fb else "corner"),
                            twist_frac=round(inv / (n * (n - 1) / 2), 4), orient=P.orient(part),
                            window_overlap_um=round(ov, 1))
    return res


def hard_core_rects(P):
    """[(part, inst, module, die rect)] for every placed hard core."""
    out = []
    for n, p in P.parts.items():
        t = P.ptype(n)
        for hc in t.get("hard_cores", []) or []:
            if "origin_um" not in hc or "outline_um" not in hc:
                continue
            x, y = hc["origin_um"]
            w, h = hc["outline_um"]
            a = P.to_die(n, (x, y))
            b = P.to_die(n, (x + w, y + h))
            out.append((n, hc.get("inst"), hc.get("module"), (min(a[0], b[0]), min(a[1], b[1]),
                                                               max(a[0], b[0]), max(a[1], b[1]))))
    return out


def metrics(S, C, raw, P, geo, g0=None):
    m = {}
    W, H = P.W, P.H
    m["die"] = dict(name=P.name, outline_um=[W, H], area_mm2=round(W * H / 1e6, 2), aspect=round(max(W, H) / min(W, H), 3),
                    parts=len(P.parts), types=len(P.types), ports=len(P.ports), lanes=len(P.lanes),
                    reach_um=P.reach, period_ps=raw["die"].get("period_ps"))
    # partitions: area coverage, aspect, slivers
    part_area = 0.0
    asp, thin = [], []
    for n in P.parts:
        x0, y0, x1, y1 = P.rect(n)
        w, h = x1 - x0, y1 - y0
        part_area += w * h
        asp.append((max(w, h) / max(min(w, h), 1e-3), n, P.parts[n]["type"], round(w, 1), round(h, 1)))
        thin.append((min(w, h), n, P.parts[n]["type"], round(w, 1), round(h, 1)))
    asp.sort(reverse=True)
    thin.sort()
    chan = sum((c[2] - c[0]) * (c[3] - c[1]) for c in (P.channel_rect(c) for c in P.die.get("channels", [])))
    m["coverage"] = dict(part_frac=round(part_area / (W * H), 4), channel_frac=round(chan / (W * H), 4),
                         uncovered_frac=round(1 - (part_area + chan) / (W * H), 4))
    m["worst_aspect"] = [dict(ratio=round(a, 2), part=n, type=t, w=w, h=h) for a, n, t, w, h in asp[:8]]
    m["thinnest"] = [dict(min_dim_um=round(d, 1), part=n, type=t, w=w, h=h) for d, n, t, w, h in thin[:8]]
    # types / instances / orients
    inst = defaultdict(list)
    for n, p in P.parts.items():
        inst[p["type"]].append(P.orient(n))
    m["types"] = dict(count=len(P.types), replicated=sum(1 for v in inst.values() if len(v) > 1),
                      singletons=sum(1 for v in inst.values() if len(v) == 1),
                      max_inst=max((len(v), k) for k, v in inst.items())[::-1],
                      mixed_orient=sorted([k for k, v in inst.items() if len(set(v)) > 1])[:40])
    # lanes: length, bits*um, hops vs reach, cycles, twists (order flips)
    rows = []
    try:
        pads = P.lane_pads()
    except Exception:
        pads = {}
    for lid, (pts, regs, xs) in geo.items():
        L = plen(pts)
        w = lane_width(P, lid)
        hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(regs, regs[1:])]
        reach = float(P.lanes[lid].get("reach_um", P.reach))
        orders = [P.ports[p].get("order", "lsb_low") for p in P.lanes[lid]["ports"]]
        flips = sum(1 for a, b in zip(orders, orders[1:]) if a != b)
        try:
            cyc = P.lane_natural(lid)["cycles"] + int(pads.get(lid, 0) or 0)
        except Exception:
            cyc = None
        rows.append(dict(lane=lid, bits=w, len_um=round(L, 1), bit_mm=round(w * L / 1000, 1), hops=len(hops),
                         max_hop_um=round(max(hops) if hops else 0, 1), reach_um=reach,
                         hop_ratio=round((max(hops) if hops else 0) / reach, 3), cycles=cyc, order_flips=flips,
                         um_per_cycle=round(L / cyc, 1) if cyc else None))
    tot_bitmm = sum(r["bit_mm"] for r in rows)
    m["wire"] = dict(total_bit_m=round(tot_bitmm / 1000, 2),
                     top_bit_mm=sorted(rows, key=lambda r: -r["bit_mm"])[:15],
                     longest=sorted(rows, key=lambda r: -r["len_um"])[:10],
                     worst_hop=sorted(rows, key=lambda r: -r["hop_ratio"])[:10],
                     hops_over_reach=sum(1 for r in rows if r["hop_ratio"] > 1.0 + 1e-6),
                     hops_over_0p9=sum(1 for r in rows if r["hop_ratio"] > 0.9),
                     lanes_with_order_flips=sum(1 for r in rows if r["order_flips"]),
                     flip_examples=[r["lane"] for r in rows if r["order_flips"]][:10],
                     wide_long=[r for r in sorted(rows, key=lambda r: -r["bits"]) if r["len_um"] > 2 * P.reach][:10])
    top10 = sorted(rows, key=lambda r: -r["bit_mm"])[:max(1, len(rows) // 10)]
    m["wire"]["top10pct_share"] = round(sum(r["bit_mm"] for r in top10) / max(tot_bitmm, 1e-9), 3)
    tw = twists(P)
    # with H and V on different layers, any bit permutation routes as L / Z / C shapes without same-layer overlap and
    # at the same total wirelength as long as the in and out windows do not overlap along the shared axis.  A twist
    # costs only for straight / U-turn crossings whose windows overlap (the reversed bits then need jogs).
    bad = sorted((v for v in tw.values() if v["twist_frac"] > 0.01 and v["kind"] != "corner"
                  and v["window_overlap_um"] > 0),
                 key=lambda v: -v["twist_frac"] * v["bits"])
    m["twist"] = dict(crossings=len(tw), any_twisted=sum(1 for v in tw.values() if v["twist_frac"] > 0.01),
                      corner_twisted=sum(1 for v in tw.values() if v["twist_frac"] > 0.01
                                                             and v["kind"] == "corner"), twisted=len(bad), twisted_bits=sum(v["bits"] for v in bad),
                      full_reversals=sum(1 for v in bad if v["twist_frac"] > 0.99), worst=bad[:15],
                      by_type=sorted({(v["type"], v["slot"], v["orient"], v["twist_frac"]) for v in bad})[:40])
    # seams
    sm = seams(P)
    srt = sorted(sm.items(), key=lambda kv: -kv[1]["bits_per_um"])
    m["seams"] = dict(count=len(sm), worst=[dict(parts=list(k), face=v["face"], bits=v["bits"], ports=v["ports"],
                                                 len_um=round(v["len"], 1), bits_per_um=v["bits_per_um"])
                                            for k, v in srt[:12]])
    # clock
    root = P.clock.get("spine", {}).get("root_um")
    taps = {}
    for n in P.parts:
        ck = P.ptype(n).get("clock", {})
        if "tap_um" in ck:
            taps[n] = P.to_die(n, ck["tap_um"])
    cl = dict(root_um=root, topology=P.clock.get("spine", {}).get("topology"), taps=len(taps),
              neighbour_skew_ps=P.clock.get("neighbour_skew_ps"), face_xing=P.clock.get("face_xing"))
    if root and taps:
        d = sorted(abs(t[0] - root[0]) + abs(t[1] - root[1]) for t in taps.values())
        cl.update(root_tap_min_um=round(d[0]), root_tap_max_um=round(d[-1]), root_tap_p50_um=round(d[len(d) // 2]),
                  root_off_centre_um=[round(root[0] - W / 2, 1), round(root[1] - H / 2, 1)])
        # neighbour pairs across seams: difference of root->tap distance (H-tree-equal assumption breaks when large)
        dd = []
        for (a, b), v in sm.items():
            if a in taps and b in taps:
                da = abs(taps[a][0] - root[0]) + abs(taps[a][1] - root[1])
                db = abs(taps[b][0] - root[0]) + abs(taps[b][1] - root[1])
                dd.append((abs(da - db), a, b))
        dd.sort(reverse=True)
        cl["seam_root_dist_delta_worst"] = [dict(um=round(x), a=a, b=b) for x, a, b in dd[:8]]
    m["clock"] = cl
    # hard cores
    hcs = hard_core_rects(P)
    by_part = defaultdict(float)
    halo = []
    for n, inst_, mod, (x0, y0, x1, y1) in hcs:
        by_part[n] += (x1 - x0) * (y1 - y0)
        px0, py0, px1, py1 = P.rect(n)
        halo.append((min(x0 - px0, y0 - py0, px1 - x1, py1 - y1), n, inst_, mod))
    halo.sort(key=lambda r: r[0])
    fill = sorted(((a / ((P.rect(n)[2] - P.rect(n)[0]) * (P.rect(n)[3] - P.rect(n)[1])), n) for n, a in by_part.items()),
                  reverse=True)
    # ft stations / lane routes vs hard cores: a station inside a macro outline cannot be placed; a partition-level
    # (<= M7) ft route over a macro has to detour around it or use the die layers over it
    from collections import defaultdict as _dd
    cores_of = _dd(list)
    for n, i_, mo, r in hcs:
        cores_of[n].append((r, i_, mo))
    def inside(pt, r, eps=0.5):
        return r[0] + eps < pt[0] < r[2] - eps and r[1] + eps < pt[1] < r[3] - eps
    st_in, over = [], 0.0
    st_tot = 0
    for lid, (pts, regs, xs) in geo.items():
        for p in regs[1:-1]:
            st_tot += 1
            for n, cl in cores_of.items():
                pr = P.rect(n)
                if not inside(p, pr, 0):
                    continue
                for r, i_, mo in cl:
                    if inside(p, r):
                        decl = any(bool((P.slot(x["part"], x["slot"]) or {}).get("regs_um")) for x in xs
                                   if x["part"] == n and x["slot"])
                        st_in.append(dict(lane=lid, part=n, type=P.parts[n]["type"], core=i_, module=mo,
                                          declared=decl, xy=[round(p[0], 1), round(p[1], 1)]))
                break
    by_type = _dd(int)
    for d in st_in:
        by_type[d["type"]] += 1
    m["stations_in_cores"] = dict(stations=st_tot, inside_core=len(st_in),
                                  declared_inside=sum(1 for d in st_in if d["declared"]),
                                  declared_examples=[d for d in st_in if d["declared"]][:12], by_type=dict(sorted(by_type.items(), key=lambda kv: -kv[1])[:20]),
                                  examples=st_in[:12])
    m["hard_cores"] = dict(placed=len(hcs), parts_with_cores=len(by_part),
                           core_area_frac_die=round(sum(by_part.values()) / (W * H), 4),
                           densest_parts=[dict(part=n, type=P.parts[n]["type"], fill=round(f, 3)) for f, n in fill[:8]],
                           outside_outline=[dict(part=n, inst=i, module=mo, edge_um=round(e, 2))
                                            for e, n, i, mo in halo if e < -1e-6][:10],
                           tight_to_edge=[dict(part=n, inst=i, module=mo, edge_um=round(e, 2))
                                          for e, n, i, mo in halo if -1e-6 <= e < 4.32][:10],
                           n_tight_to_edge=sum(1 for e, *_ in halo if -1e-6 <= e < 4.32))
    # die io
    io = []
    for w in P.die.get("io") or []:
        x0, y0, x1, y1 = w["rect_um"]
        io.append(dict(name=w.get("name") or w.get("part"), iface=w.get("iface"), host=w.get("host"),
                       edge_um=round(min(x0, y0, W - x1, H - y1), 1)))
    m["die_io"] = io
    if g0:
        s = g0.get("summary", {})
        m["g0"] = dict(errors=s.get("errors"), warnings=s.get("warnings"), worst_cut=s.get("worst_cut"),
                       worst_segment=s.get("worst_segment"), g0c=(s.get("g0c") or {}).get("errors")
                       if isinstance(s.get("g0c"), dict) else None)
    return m, rows, sm, taps, hcs


def heat(P, geo, binum=100.0):
    import numpy as np
    nx, ny = int(math.ceil(P.W / binum)), int(math.ceil(P.H / binum))
    A = np.zeros((ny, nx))
    for lid, (pts, regs, xs) in geo.items():
        w = lane_width(P, lid)
        for a, b in zip(pts, pts[1:]):
            L = abs(a[0] - b[0]) + abs(a[1] - b[1])
            n = max(1, int(L / (binum / 2)))
            for k in range(n):
                t = (k + 0.5) / n
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                i, j = min(ny - 1, max(0, int(y / binum))), min(nx - 1, max(0, int(x / binum)))
                A[i, j] += w * L / n
    return A / (binum * binum) * binum   # bits crossing per um (bit-um per bin / bin side / bin side * bin side)


def draw_base(ax, P, geo, hcs, taps, sm=None, rect=None, lanes=True, labels=False, hl_lanes=(), hl_seams=()):
    from matplotlib.patches import Rectangle
    from matplotlib.collections import LineCollection, PatchCollection
    import matplotlib.pyplot as plt
    cmap = plt.get_cmap("tab20")
    tcol = {t: cmap(i % 20) for i, t in enumerate(sorted(P.types))}
    W, H = P.W, P.H
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.0, ec="black"))
    for c in P.die.get("channels", []):
        x0, y0, x1, y1 = P.channel_rect(c)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="khaki", ec="grey", hatch="//", lw=0.3, alpha=0.5))
    vis = (lambda r: True) if rect is None else (lambda r: not (r[2] < rect[0] or r[0] > rect[2] or r[3] < rect[1] or r[1] > rect[3]))
    pp = []
    for n, p in P.parts.items():
        r = P.rect(n)
        if not vis(r):
            continue
        pp.append(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=tcol[p["type"]], alpha=0.3, ec="black", lw=0.4))
        if labels:
            o = P.orient(n)
            ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, f"{n}\n{p['type']}" + ("" if o == "R0" else f" {o}"),
                    ha="center", va="center", fontsize=5, zorder=8, clip_on=True)
    ax.add_collection(PatchCollection(pp, match_original=True))
    cp = [Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1]) for _, _, _, r in hcs if vis(r)]
    ax.add_collection(PatchCollection(cp, fc="dimgray", ec="black", lw=0.2, alpha=0.75, zorder=2))
    for w in P.die.get("io") or []:
        x0, y0, x1, y1 = w["rect_um"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="magenta", hatch="xx", lw=0.8, zorder=6))
    if lanes:
        wmax = max([lane_width(P, l) for l in P.lanes] + [1])
        segs, lws, cols = [], [], []
        for lid, (pts, regs, _) in geo.items():
            hl = lid in hl_lanes
            segs.append(pts)
            lws.append((2.5 if hl else 0.2) + 2.0 * (lane_width(P, lid) / wmax) ** 0.5)
            cols.append("red" if hl else "teal")
        ax.add_collection(LineCollection(segs, linewidths=lws, colors=cols, alpha=0.6, zorder=3))
        sx = [p[0] for lid, (pts, regs, _) in geo.items() for p in regs[1:-1]]
        sy = [p[1] for lid, (pts, regs, _) in geo.items() for p in regs[1:-1]]
        ax.scatter(sx, sy, s=3 if rect else 0.6, c="navy", zorder=4, linewidths=0)
    tx = [t[0] for t in taps.values()]
    ty = [t[1] for t in taps.values()]
    ax.scatter(tx, ty, s=12 if rect else 3, marker="*", c="darkorange", zorder=6, linewidths=0)
    root = P.clock.get("spine", {}).get("root_um")
    if root:
        ax.plot([root[0]], [root[1]], marker="P", ms=9, color="crimson", zorder=7)
    if sm is not None:
        segs, cols, lws = [], [], []
        bmax = max([v["bits_per_um"] for v in sm.values()] + [1e-9])
        for k, v in sm.items():
            if v["axis"] == "x":
                seg = [(v["at"], v["lo"]), (v["at"], v["hi"])]
            else:
                seg = [(v["lo"], v["at"]), (v["hi"], v["at"])]
            segs.append(seg)
            hl = k in hl_seams
            cols.append("red" if hl else plt.get_cmap("inferno_r")(0.15 + 0.85 * v["bits_per_um"] / bmax))
            lws.append(3.0 if hl else 1.6)
        ax.add_collection(LineCollection(segs, colors=cols, linewidths=lws, zorder=5))
    if rect is None:
        ax.set_xlim(-0.01 * W, 1.01 * W)
        ax.set_ylim(-0.01 * H, 1.01 * H)
    else:
        ax.set_xlim(rect[0], rect[2])
        ax.set_ylim(rect[1], rect[3])
    ax.set_aspect("equal")
    ax.tick_params(labelsize=6)


def render_all(P, geo, m, rows, sm, taps, hcs, out):
    import warnings
    warnings.filterwarnings("ignore")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    out = Path(out)
    W, H = P.W, P.H
    sc = 14.0 / max(W, H)
    files = {}

    def fig_die():
        return plt.subplots(figsize=(W * sc + 1.0, H * sc + 0.8), dpi=150)

    # 1. die + cores + seams coloured by bits/um
    fig, ax = fig_die()
    draw_base(ax, P, geo, hcs, taps, sm=sm, labels=len(P.parts) <= 140)
    ax.set_title(f"{P.name}: partitions (type colour), hard cores (grey), lanes (teal, width~sqrt bits), stations "
                 f"(navy), taps (*), root (+), seams coloured by bits/um (dark = dense); IO magenta", fontsize=7)
    fig.tight_layout()
    files["die_cores"] = str(out / "die_cores.png")
    fig.savefig(files["die_cores"])
    plt.close(fig)
    # 2. heat map of routed bits
    A = heat(P, geo)
    fig, ax = fig_die()
    im = ax.imshow(np.log10(1 + A), origin="lower", extent=(0, A.shape[1] * 100, 0, A.shape[0] * 100), cmap="magma_r")
    for n in P.parts:
        r = P.rect(n)
        ax.add_patch(matplotlib.patches.Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, lw=0.2, ec="grey"))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    plt.colorbar(im, ax=ax, fraction=0.03, label="log10(1 + plan lane bits crossing per 100-um bin)")
    ax.set_title(f"{P.name}: plan lane bit density (Manhattan plan routes; partition outlines grey)", fontsize=8)
    fig.tight_layout()
    files["die_wire"] = str(out / "die_wire.png")
    fig.savefig(files["die_wire"])
    plt.close(fig)
    m["wire"]["peak_bits_per_bin"] = float(A.max())
    i, j = np.unravel_index(A.argmax(), A.shape)
    m["wire"]["peak_at_um"] = [j * 100 + 50, i * 100 + 50]

    # zooms
    def zoom(name, cx, cy, half, title, hl_lanes=(), hl_seams=()):
        half = max(half, 400.0)
        r = (max(0, cx - half), max(0, cy - half), min(W, cx + half), min(H, cy + half))
        fig, ax = plt.subplots(figsize=(8, 8 * (r[3] - r[1]) / max(r[2] - r[0], 1)), dpi=150)
        draw_base(ax, P, geo, hcs, taps, sm=sm, rect=r, labels=True, hl_lanes=hl_lanes, hl_seams=hl_seams)
        ax.set_title(title, fontsize=7)
        fig.tight_layout()
        f = str(out / f"zoom_{name}.png")
        fig.savefig(f)
        plt.close(fig)
        files[f"zoom_{name}"] = f

    px, py = m["wire"]["peak_at_um"]
    zoom("dense", px, py, 1500, f"densest lane bin at ({px:.0f},{py:.0f}): {A.max():.0f} bits / 100-um bin")
    lg = m["wire"]["longest"][0]["lane"]
    pts = geo[lg][0]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    zoom("longest", (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 300,
         f"longest lane {lg}: {m['wire']['longest'][0]['len_um']:.0f} um, {m['wire']['longest'][0]['bits']} b, "
         f"{m['wire']['longest'][0]['cycles']} cyc (red)", hl_lanes={lg})
    wb = m["wire"]["top_bit_mm"][0]["lane"]
    pts = geo[wb][0]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    zoom("widest_cost", (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
         max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 300,
         f"largest bit*mm lane {wb}: {m['wire']['top_bit_mm'][0]['bit_mm']} bit-mm (red)", hl_lanes={wb})
    if sm:
        k, v = max(sm.items(), key=lambda kv: kv[1]["bits_per_um"])
        c = (v["at"], (v["lo"] + v["hi"]) / 2) if v["axis"] == "x" else ((v["lo"] + v["hi"]) / 2, v["at"])
        zoom("seam", c[0], c[1], max(v["len"] / 2 + 200, 800),
             f"densest seam {k[0]}|{k[1]}: {v['bits']} b over {v['len']:.0f} um = {v['bits_per_um']} b/um (red)",
             hl_seams={k})
    root = P.clock.get("spine", {}).get("root_um")
    if root:
        zoom("clock_root", root[0], root[1], 2000, f"clock spine root {root} and nearby taps")
    if P.die.get("io"):
        w = P.die["io"][0]
        x0, y0, x1, y1 = w["rect_um"]
        zoom("io", (x0 + x1) / 2, (y0 + y1) / 2, 1500, f"die IO window {w.get('name') or w.get('part')} ({w.get('iface')})")
    if m["hard_cores"]["densest_parts"]:
        n = m["hard_cores"]["densest_parts"][0]["part"]
        r = P.rect(n)
        zoom("cores", (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, max(r[2] - r[0], r[3] - r[1]) / 2 + 100,
             f"most hard-core-filled partition {n} ({P.parts[n]['type']}), fill {m['hard_cores']['densest_parts'][0]['fill']}")
    t = m["thinnest"][0]
    r = P.rect(t["part"])
    zoom("thin", (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, max(r[2] - r[0], r[3] - r[1]) / 2 + 200,
         f"thinnest partition {t['part']} ({t['type']}) {t['w']} x {t['h']} um")
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--tools", default=str(Path(__file__).resolve().parent.parent / "die_plan"))
    ap.add_argument("--g0")
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    S, C, raw, P, geo = load(a.tools, a.plan)
    g0 = json.load(open(a.g0)) if a.g0 else None
    m, rows, sm, taps, hcs = metrics(S, C, raw, P, geo, g0)
    m["files"] = render_all(P, geo, m, rows, sm, taps, hcs, a.out)
    json.dump(m, open(Path(a.out) / "review.json", "w"), indent=1, default=str)
    print(json.dumps({k: m[k] for k in ("die", "coverage", "clock")}, default=str))


if __name__ == "__main__":
    main()
