#!/usr/bin/env python3
"""chain_resite.py (FP-CONVERGE-S81 11-25): re-site the registers of station chains whose hop is over the GATE reach.

After a type grows (leaf_grow) or its cores move (core_place), the pin windows stay on the faces while the registers
follow the cores, so the first or last hop of a chain stretches (t10 leafdn_i0: window worst end (744.6, 0) -> first
register (1088, 168) = 512 um).  Pin windows cannot move (parents abut), so the registers are re-placed instead:

  chain_resite.py run PLAN OUT --types T[,T] [--cap 404] [--extra-reg] [--ops OPS.json] [--report REP.json]

Every chain (internal_stations from -> regs -> to; ft_slots in pin -> mid regs -> out pin, same pin and worst-bit
rules as precheck.reach_findings) with a hop over --gate (405 um) gets its registers re-placed by a DP over legal
lattice sites: inside the outline (8 um inset), outside every hard core (1 um halo), all hops <= --cap, minimal
displacement, SAME register count (zero cycles).  A chain with no such placement is retried with one extra register
when --extra-reg (internal_stations only: +1 cycle, listed under 'latency'), else it is reported under 'skipped'.
Exact station bit-site groups move rigidly with their register on the row grid. A moved bank's full cell
footprints must avoid placement obstacles, even when its register centre was already in reach.
Writes OUT (the plan with the rows applied) and OPS (plan_ops.v1 replace ops carrying the old values)."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "precheck"))
import adv_geom_static as AG  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402
import precheck as PC  # noqa: E402

HALO, INSET, G = 1.0, 8.0, 4.32
SITE_W, ROW_H = 0.054, 0.27


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def respace(pts, k):
    """k points at equal Manhattan arc fractions along the polyline pts"""
    seg = [man(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    out = []
    for j in range(1, k + 1):
        s = total * j / (k + 1)
        acc = 0.0
        for i, g in enumerate(seg):
            if acc + g >= s or i == len(seg) - 1:
                f = 0.0 if g == 0 else (s - acc) / g
                out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f))
                break
            acc += g
    return out


def legal_box(p, offs, rects, w, h, *, inset=INSET):
    """a register at p with its bit-site group (offs = (dx0, dy0, dx1, dy1) bounding box, or None) is legal"""
    x0, y0, x1, y1 = (p[0], p[1], p[0], p[1]) if offs is None else (p[0] + offs[0], p[1] + offs[1], p[0] + offs[2], p[1] + offs[3])
    if x0 < inset or y0 < inset or x1 > w - inset or y1 > h - inset:
        return False
    return not any(r[0] < x1 and x0 < r[2] and r[1] < y1 and y0 < r[3] for r in rects)


def cands(target, offs, rects, w, h, n=400, rmax=160, *, anchor=None):
    tx, ty = target
    if anchor is not None:
        tx, ty = (origin + round((v - origin) / pitch) * pitch
                  for v, origin, pitch in zip(target, anchor, (SITE_W, ROW_H)))
    out = []
    for ring in range(rmax):
        pts = [(tx, ty)] if ring == 0 else []
        if ring:
            for i in range(-ring, ring + 1):
                pts += [(tx + i * G, ty - ring * G), (tx + i * G, ty + ring * G), (tx - ring * G, ty + i * G), (tx + ring * G, ty + i * G)]
        for p in pts:
            digits = 6 if anchor is not None else 3
            p = (round(p[0], digits), round(p[1], digits))
            if legal_box(p, offs, rects, w, h):
                out.append(p)
        if len(out) >= n:
            break
    return out[:n]


def place_chain(pts, k, offs_list, rects, w, h, cap, *, anchors=None):
    """DP: k registers, hops <= cap, minimal total displacement from the equal-arc targets; None when infeasible"""
    tg = respace(pts, k)
    cs = [cands(t, offs_list[j] if j < len(offs_list) else None, rects, w, h,
                anchor=anchors[j] if anchors is not None else None) for j, t in enumerate(tg)]
    if any(not c for c in cs):
        return None
    start, end = tuple(pts[0]), tuple(pts[-1])
    inf = 1e18
    cost = [{p: (man(p, tg[0]) if man(start, p) <= cap else inf) for p in cs[0]}]
    back = [{}]
    for j in range(1, k):
        cj, bj = {}, {}
        for p in cs[j]:
            best = (inf, None)
            for q, c in cost[j - 1].items():
                if c < inf and man(q, p) <= cap:
                    v = c + man(p, tg[j])
                    if v < best[0]:
                        best = (v, q)
            cj[p], bj[p] = best
        cost.append(cj)
        back.append(bj)
    fin = min(((c, p) for p, c in cost[-1].items() if c < inf and man(p, end) <= cap), default=None)
    if fin is None:
        return None
    seq = [fin[1]]
    for j in range(k - 1, 0, -1):
        seq.append(back[j][seq[-1]])
    return [list(p) for p in reversed(seq)]


def chain_points(t, e):
    """[from, regs..., to] of an internal_stations entry with the worst-bit window end, as precheck measures it"""
    w, h = t.get("outline_um") or (0, 0)
    pts = [tuple(e["from_um"])] + [tuple(r) for r in (e.get("regs_um") or [])] + [tuple(e["to_um"])]
    conn = e.get("conn", "")
    buses = {b.get("name"): b for b in t.get("buses") or []}
    bus = buses.get(conn[4:]) if conn.startswith("bus:") else None
    if bus and bus.get("face") in ("N", "S", "E", "W") and bus.get("window_um") and len(pts) >= 2:
        if bus.get("dir") == "in" and PC.on_face(bus["face"], pts[0], w, h):
            pts[0] = PC.face_end_worst(bus["face"], bus["window_um"], w, h, pts[1])
        elif bus.get("dir") == "out" and PC.on_face(bus["face"], pts[-1], w, h):
            pts[-1] = PC.face_end_worst(bus["face"], bus["window_um"], w, h, pts[-2])
    return pts


def hops(pts):
    return [man(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]


def group_box(group, reg, cell):
    xs = [s[0] - reg[0] for s in group]
    ys = [s[1] - reg[1] for s in group]
    return min(xs), min(ys), max(xs) + cell[0], max(ys) + cell[1]


def sites_collide(groups, cell, rects, w, h):
    for group in groups:
        for x, y in group:
            if not legal_box((x, y), (0, 0, *cell), rects, w, h, inset=0):
                return True
    return False


def translate_groups(groups, before, after):
    return [[[round(x + new[0] - old[0], 6), round(y + new[1] - old[1], 6)]
             for x, y in group] for group, old, new in zip(groups, before, after)]

ROUTED_CAPS = (404.0, 380.0, 350.0, 320.0)   # tighter Manhattan caps tried until the OBSTACLE-AVOIDING hop is <= gate


def routed_max(t, pts):
    """FP-CONVERGE-S81 (Fable: t10 internal hops >405 um routed 1 -> 14, t50 14 -> 29: precheck REACH is Manhattan only):
    max hop of the chain in hub_repack's obstacle model (a hop whose L-routes cross a core is the street A* length)"""
    import hub_repack as HR
    w, h = t.get("outline_um") or (0, 0)
    R = HR.Raster(w, h, [r[:4] for r in AG.hard_rects(t)], halo=HALO)
    return HR.chain_metrics(R, pts)[0]


def place_routed(t, pts, k, offs_list, rects, w, h, cap, gate, routed=True, *, anchors=None):
    """place_chain, accepted only when its routed max hop is <= gate; tries tighter Manhattan caps; None when infeasible"""
    caps = [c for c in ROUTED_CAPS if c <= cap] or [cap]
    for c in (caps if routed else caps[:1]):
        new = place_chain(pts, k, offs_list, rects, w, h, c, anchors=anchors)
        if new is None:
            return None
        if not routed or routed_max(t, [pts[0]] + [tuple(r) for r in new] + [pts[-1]]) <= gate:
            return new
    return None


def resite_type(name, t, gate=405.0, cap=404.0, extra_reg=False, routed=True, whole_bus=True):
    """-> (ops, latency, skipped) for type t (t is NOT modified).  routed: a chain whose obstacle-avoiding hop is over the
    gate is re-sited too and a placement is accepted only when its routed hop is <= gate; whole_bus: with extra_reg, a bus that
    needs +1 gets it on EVERY chain of that bus (conn) so the lane keeps one latency (leafdn_i0 rb_d 32 bits stayed uneven)"""
    w, h = t.get("outline_um") or (0, 0)
    rects = [(x0 - HALO, y0 - HALO, x1 + HALO, y1 + HALO) for x0, y0, x1, y1, _ in AG.hard_rects(t)]
    ops, latency, skipped = [], [], []
    plus1 = set()
    ents = t.get("internal_stations") or []
    slots = t.get("ft_slots") or []
    exact_conns = {e.get("conn") for e in ents if e.get("bit_sites_um") is not None}
    exact_rects = list(placement_boxes(t, halo=HALO).values()) if exact_conns or any(
        s.get("bit_sites_um") is not None for s in slots) else []
    for i, e in enumerate(ents):
        if not e.get("from_um") or not e.get("to_um") or not e.get("regs_um"):
            continue
        pts = chain_points(t, e)
        regs = [list(r) for r in e["regs_um"]]
        groups = e.get("bit_sites_um")
        cell = e.get("bit_site_cell_um")
        k = len(regs)
        if groups is not None and (len(groups) != k or not cell or not all(groups)):
            skipped.append({"type": name, "index": i, "conn": e.get("conn"), "why": "invalid exact bit-bank geometry"})
            continue
        bad_bank = groups and sites_collide(groups, cell, exact_rects, w, h)
        if not bad_bank and max(hops(pts)) <= gate and (not routed or routed_max(t, pts) <= gate):
            continue
        offs = [group_box(g, r, cell) for g, r in zip(groups, regs)] if groups else [None] * k
        new = place_routed(t, pts, k, offs, exact_rects if groups else rects, w, h, cap, gate, routed,
                           anchors=regs if groups else None)
        path = f"/partition_types/{name}/internal_stations/{i}"
        if new is None and extra_reg and groups is None and (not whole_bus or e.get("conn") not in exact_conns):
            new = place_routed(t, pts, k + 1, [None] * (k + 1), rects, w, h, cap, gate, routed)
            if new is not None:
                latency.append({"type": name, "index": i, "conn": e.get("conn"), "bits": e.get("bits"), "regs": k, "new_regs": k + 1})
                plus1.add(e.get("conn"))
        if new is None:
            skipped.append({"type": name, "index": i, "conn": e.get("conn"), "why": f"no legal placement <= {cap} um" + (" (routed)" if routed else "")})
            continue
        ops.append({"op": "replace", "path": path + "/regs_um", "old": regs, "value": new})
        if groups:
            ops.append({"op": "replace", "path": path + "/bit_sites_um", "old": groups,
                        "value": translate_groups(groups, regs, new)})
    if extra_reg and whole_bus and plus1:
        for i, e in enumerate(ents):
            if e.get("conn") not in plus1 or not e.get("from_um") or not e.get("to_um") or not e.get("regs_um"):
                continue
            if any(l["index"] == i for l in latency):
                continue
            pts = chain_points(t, e)
            regs = [list(r) for r in e["regs_um"]]
            k = len(regs)
            new = place_routed(t, pts, k + 1, [None] * (k + 1), rects, w, h, cap, gate, routed)
            path = f"/partition_types/{name}/internal_stations/{i}/regs_um"
            if new is None:
                skipped.append({"type": name, "index": i, "conn": e.get("conn"), "why": "whole-bus +1 register: no legal placement"})
                continue
            ops = [o for o in ops if o["path"] != path]
            ops.append({"op": "replace", "path": path, "old": regs, "value": new})
            latency.append({"type": name, "index": i, "conn": e.get("conn"), "bits": e.get("bits"), "regs": k, "new_regs": k + 1, "whole_bus": True})
    for si, s in enumerate(slots):
        k = int(s.get("stations", 1) or 1)
        regs = [list(r) for r in s.get("regs_um") or []]
        if k < 2 or len(regs) < k - 1:
            continue
        first = len(regs) - (k - 1)
        mid = regs[first:]
        groups = s.get("bit_sites_um")
        cell = s.get("bit_site_cell_um")
        if groups is not None and (len(groups) not in (len(mid), k) or not cell or not all(groups)):
            skipped.append({"type": name, "slot": s.get("name"), "why": "invalid exact bit-bank geometry"})
            continue
        in_face, out_face = s.get("in_face"), s.get("out_face")
        in_window, out_window = s.get("in_window_um"), s.get("out_window_um")
        a = PC.face_point(in_face, in_window, w, h, tuple(mid[0])) if in_face and in_window else None
        b = PC.face_point(out_face, out_window, w, h, tuple(mid[-1])) if out_face and out_window else None
        if not groups and (a is None or b is None):
            continue
        # A generated pin window need not be in the plan. Preserve the nearest
        # register on an unknown face unless the plan provides its stage-0 seat.
        if a is None and first and in_face in ("N", "S", "E", "W") and PC.on_face(in_face, regs[first - 1], w, h):
            a = regs[first - 1]
        left = int(a is None)
        right = len(mid) - int(b is None)
        a = mid[0] if a is None else a
        b = mid[-1] if b is None else b
        movable = mid[left:right]
        movable_groups = groups[-len(mid):] if groups else []
        bad_bank = groups and sites_collide(movable_groups, cell, exact_rects, w, h)
        if bad_bank and sites_collide(movable_groups[:left] + movable_groups[right:], cell, exact_rects, w, h):
            skipped.append({"type": name, "slot": s.get("name"), "why": "blocked edge bank needs an exact face window"})
            continue
        pts = [tuple(a)] + [tuple(r) for r in movable] + [tuple(b)]
        if not bad_bank and max(hops(pts)) <= gate:
            continue
        if not movable:
            skipped.append({"type": name, "slot": s.get("name"), "why": "no movable stage between fixed endpoints"})
            continue
        move_groups = movable_groups[left:right]
        offs = [group_box(g, r, cell) for g, r in zip(move_groups, movable)]
        new_mid = place_chain(pts, len(movable), offs, exact_rects if move_groups else rects,
                              w, h, cap, anchors=movable if move_groups else None)
        if new_mid is None:
            skipped.append({"type": name, "slot": s.get("name"), "why": f"no legal placement <= {cap} um"})
            continue
        path = f"/partition_types/{name}/ft_slots/{si}"
        new_regs = regs[:first + left] + new_mid + regs[first + right:]
        ops.append({"op": "replace", "path": path + "/regs_um", "old": regs, "value": new_regs})
        if move_groups:
            g0 = len(groups) - len(mid)
            new_groups = groups[:g0 + left] + translate_groups(move_groups, movable, new_mid) + groups[g0 + right:]
            ops.append({"op": "replace", "path": path + "/bit_sites_um", "old": groups, "value": new_groups})
    return ops, latency, skipped


def _walk(root, parts):
    cur = root
    for p in parts[:-1]:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    return cur, parts[-1]


def apply_ops(plan, ops):
    for o in ops:
        parts = o["path"].strip("/").split("/")
        cur, last = _walk(plan, parts)
        key = int(last) if isinstance(cur, list) else last
        if cur[key] != o["old"]:
            raise ValueError(f"old value mismatch at {o['path']}")
        cur[key] = o["value"]
    return plan


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run")
    r.add_argument("plan")
    r.add_argument("out")
    r.add_argument("--types", required=True)
    r.add_argument("--gate", type=float, default=405.0)
    r.add_argument("--cap", type=float, default=404.0)
    r.add_argument("--extra-reg", action="store_true")
    r.add_argument("--no-routed", action="store_true", help="Manhattan hops only (the pre-Fable behaviour)")
    r.add_argument("--no-whole-bus", action="store_true", help="with --extra-reg: +1 only on the failing chains, not on the whole bus")
    r.add_argument("--ops")
    r.add_argument("--report")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    ops, lat, sk = [], [], []
    for name in [x for x in a.types.split(",") if x]:
        t = plan["partition_types"][name]
        o, l, s = resite_type(name, t, a.gate, a.cap, a.extra_reg, not a.no_routed, not a.no_whole_bus)
        ops += o
        lat += l
        sk += s
    apply_ops(plan, ops)
    json.dump(plan, open(a.out, "w"), separators=(",", ":"))
    if a.ops:
        json.dump({"schema": "plan_ops.v1", "ops": ops}, open(a.ops, "w"))
    rep = {"ops": len(ops), "latency": lat, "skipped": sk}
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    print(f"chain_resite: {len(ops)} ops, {len(lat)} +1-register chains, {len(sk)} skipped -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
