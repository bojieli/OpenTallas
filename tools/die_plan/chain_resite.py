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
ft_slot bit-site groups move rigidly with their register (their bounding box must stay legal too).
Writes OUT (the plan with the rows applied) and OPS (plan_ops.v1 replace ops carrying the old values)."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "precheck"))
import adv_geom_static as AG  # noqa: E402
import precheck as PC  # noqa: E402

HALO, INSET, G = 1.0, 8.0, 4.32


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


def legal_box(p, offs, rects, w, h):
    """a register at p with its bit-site group (offs = (dx0, dy0, dx1, dy1) bounding box, or None) is legal"""
    x0, y0, x1, y1 = (p[0], p[1], p[0], p[1]) if offs is None else (p[0] + offs[0], p[1] + offs[1], p[0] + offs[2], p[1] + offs[3])
    if x0 < INSET or y0 < INSET or x1 > w - INSET or y1 > h - INSET:
        return False
    return not any(r[0] < x1 and x0 < r[2] and r[1] < y1 and y0 < r[3] for r in rects)


def cands(target, offs, rects, w, h, n=400, rmax=160):
    tx, ty = target
    out = []
    for ring in range(rmax):
        pts = [(tx, ty)] if ring == 0 else []
        if ring:
            for i in range(-ring, ring + 1):
                pts += [(tx + i * G, ty - ring * G), (tx + i * G, ty + ring * G), (tx - ring * G, ty + i * G), (tx + ring * G, ty + i * G)]
        for p in pts:
            p = (round(p[0], 3), round(p[1], 3))
            if legal_box(p, offs, rects, w, h):
                out.append(p)
        if len(out) >= n:
            break
    return out[:n]


def place_chain(pts, k, offs_list, rects, w, h, cap):
    """DP: k registers, hops <= cap, minimal total displacement from the equal-arc targets; None when infeasible"""
    tg = respace(pts, k)
    cs = [cands(t, offs_list[j] if j < len(offs_list) else None, rects, w, h) for j, t in enumerate(tg)]
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


def group_box(group, reg):
    xs = [s[0] - reg[0] for s in group]
    ys = [s[1] - reg[1] for s in group]
    return (min(xs), min(ys), max(xs), max(ys))


def resite_type(name, t, gate=405.0, cap=404.0, extra_reg=False):
    """-> (ops, latency, skipped) for type t (t is NOT modified)"""
    w, h = t.get("outline_um") or (0, 0)
    rects = [(x0 - HALO, y0 - HALO, x1 + HALO, y1 + HALO) for x0, y0, x1, y1, _ in AG.hard_rects(t)]
    ops, latency, skipped = [], [], []
    for i, e in enumerate(t.get("internal_stations") or []):
        if not e.get("from_um") or not e.get("to_um") or not e.get("regs_um"):
            continue
        pts = chain_points(t, e)
        if max(hops(pts)) <= gate:
            continue
        regs = [list(r) for r in e["regs_um"]]
        k = len(regs)
        new = place_chain(pts, k, [None] * k, rects, w, h, cap)
        path = f"/partition_types/{name}/internal_stations/{i}/regs_um"
        if new is None and extra_reg:
            new = place_chain(pts, k + 1, [None] * (k + 1), rects, w, h, cap)
            if new is not None:
                latency.append({"type": name, "index": i, "conn": e.get("conn"), "bits": e.get("bits"), "regs": k, "new_regs": k + 1})
        if new is None:
            skipped.append({"type": name, "index": i, "conn": e.get("conn"), "why": f"no legal placement <= {cap} um"})
            continue
        ops.append({"op": "replace", "path": path, "old": regs, "value": new})
    for si, s in enumerate(t.get("ft_slots") or []):
        k = int(s.get("stations", 1) or 1)
        regs = [list(r) for r in s.get("regs_um") or []]
        if not (s.get("in_face") and s.get("out_face") and s.get("in_window_um") and s.get("out_window_um")) or k < 2 or len(regs) < k - 1:
            continue
        mid = regs[-(k - 1):]
        a = PC.face_point(s["in_face"], s["in_window_um"], w, h, tuple(mid[0]))
        b = PC.face_point(s["out_face"], s["out_window_um"], w, h, tuple(mid[-1]))
        pts = [tuple(a)] + [tuple(r) for r in mid] + [tuple(b)]
        if max(hops(pts)) <= gate:
            continue
        groups = s.get("bit_sites_um")
        gl = groups if isinstance(groups, list) and len(groups) == len(mid) else None
        offs = [group_box(gl[j], mid[j]) if gl else None for j in range(len(mid))]
        new_mid = place_chain(pts, len(mid), offs, rects, w, h, cap)
        if new_mid is None:
            skipped.append({"type": name, "slot": s.get("name"), "why": f"no legal placement <= {cap} um"})
            continue
        idx = len(regs) - len(mid)
        ops.append({"op": "replace", "path": f"/partition_types/{name}/ft_slots/{si}/regs_um", "old": regs, "value": regs[:idx] + new_mid})
        if gl:
            new_groups = [[[x + (new_mid[j][0] - mid[j][0]), y + (new_mid[j][1] - mid[j][1])] for x, y in gl[j]] for j in range(len(mid))]
            ops.append({"op": "replace", "path": f"/partition_types/{name}/ft_slots/{si}/bit_sites_um", "old": groups, "value": new_groups})
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
    r.add_argument("--ops")
    r.add_argument("--report")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    ops, lat, sk = [], [], []
    for name in [x for x in a.types.split(",") if x]:
        t = plan["partition_types"][name]
        o, l, s = resite_type(name, t, a.gate, a.cap, a.extra_reg)
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
