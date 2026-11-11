#!/usr/bin/env python3
"""CPL-S81-SLICE-3: derive station re-sites (companion) and added-tap re-sites (window_tap form) for a pos delta.
usage: fix.py BASE POS_DELTA OUT_PREFIX     (run from repo/tools/die_plan for schema imports)"""
import json, sys, copy, math
sys.path.insert(0, "."); import schema
from placement_obstacles import placement_boxes
base, posp, pre = sys.argv[1:4]
P = json.load(open(base)); D = json.load(open(posp))
REACH, L, CL = 405.0, 4.32, schema.TAP_CLEAR_UM
comp, wtap, rep = {}, {}, {}
def free(p, boxes, halo):
    return not any(a - halo < p[0] < c + halo and b - halo < p[1] < d + halo for a, b, c, d in boxes)
def nearest_free(p, boxes, halo, W, H, lo=0.0):
    if free(p, boxes, halo): return [round(p[0], 3), round(p[1], 3)]
    for r in range(1, 400):
        best = None
        for i in range(-r, r + 1):
            for j in (-r + abs(i), r - abs(i)):
                q = (p[0] + i * L, p[1] + j * L)
                if lo <= q[0] <= W - lo and lo <= q[1] <= H - lo and free(q, boxes, halo):
                    best = q; break
            if best: break
        if best: return [round(best[0], 3), round(best[1], 3)]
    raise SystemExit(f"no free site near {p}")
def hops(pts): return [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]
for tn, mv in D.items():
    t0 = P["partition_types"][tn]; t = copy.deepcopy(t0); W, H = t["outline_um"]
    old = {}
    for k in ("hard_cores", "contents"):
        for e in t.get(k) or []:
            if e["inst"] in mv:
                old[e["inst"]] = (k, list(e["origin_um"]), e["outline_um"]); e["origin_um"] = mv[e["inst"]][:2]
    boxes = list(placement_boxes(t).values())
    hc_old = {i: (o[0], o[1], o[0] + s[0], o[1] + s[1], mv[i][0] - o[0], mv[i][1] - o[1]) for i, (k, o, s) in old.items() if k == "hard_cores"}
    def follow(p):
        for i, (a, b, c, d, dx, dy) in hc_old.items():
            if a - 1e-3 <= p[0] <= c + 1e-3 and b - 1e-3 <= p[1] <= d + 1e-3:
                return [round(p[0] + dx, 3), round(p[1] + dy, 3)], i
        return list(p), None
    st_out, srep = [], []
    for s in t.get("internal_stations") or []:
        f, fi = follow(s["from_um"]); to, ti = follow(s["to_um"])
        regs = [list(r) for r in s.get("regs_um") or []]
        bad = [k for k, r in enumerate(regs) if not free(r, boxes, L)]
        pts0 = [s["from_um"]] + regs + [s["to_um"]]
        if fi or ti or bad:
            # keep each reg; push only blocked ones to the nearest free lattice point; re-check hops
            regs = [r if free(r, boxes, L) else nearest_free(r, boxes, L, W, H) for r in regs]
        pts = [f] + regs + [to]
        hp = hops(pts)
        if max(hp or [0]) > REACH:
            # respace the regs evenly along the existing poly-line (same count)
            n = len(regs); poly = [f] + regs + [to]
            seg = hops(poly); tot = sum(seg)
            new = []
            for k in range(1, n + 1):
                tgt = tot * k / (n + 1); acc = 0
                for (a, b), sl in zip(zip(poly, poly[1:]), seg):
                    if acc + sl >= tgt and sl > 0:
                        u = (tgt - acc) / sl; new.append([a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])]); break
                    acc += sl
            regs = [nearest_free(r, boxes, L, W, H) for r in new]
            pts = [f] + regs + [to]; hp = hops(pts)
        for _ in range(3):
            if max(hp or [0]) <= REACH: break
            for k in range(len(regs)):
                a, b = pts[k], pts[k + 2]
                cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                best = None
                for i in range(-60, 61):
                    for j in range(-60, 61):
                        q = (cx + i * L, cy + j * L)
                        if not (0 <= q[0] <= W and 0 <= q[1] <= H) or not free(q, boxes, L): continue
                        m = max(abs(q[0] - a[0]) + abs(q[1] - a[1]), abs(q[0] - b[0]) + abs(q[1] - b[1]))
                        if best is None or m < best[0]: best = (m, q)
                if best and best[0] < max(hops(pts[k:k + 3])):
                    regs[k] = [round(best[1][0], 3), round(best[1][1], 3)]; pts = [f] + regs + [to]
            hp = hops(pts)
        st_out.append(dict(from_um=f, to_um=to, regs_um=regs))
        if pts != pts0:
            srep.append(dict(conn=s.get("conn"), max_hop_before=round(max(hops(pts0) or [0]), 1), max_hop_after=round(max(hp or [0]), 1)))
    comp[tn] = {"internal_stations": st_out}
    # added taps under any placement box (halo TAP_CLEAR) -> nearest legal lattice point
    ck = t.get("clock") or {}
    hb = list(placement_boxes(t, halo=CL).values())
    grid = schema._grid_taps(type("X", (), {"types": P["partition_types"]})(), tn) if False else []
    at = {}
    taken = [tuple(q["xy"]) for q in ck.get("added_taps") or []]
    for q in ck.get("added_taps") or []:
        x, y = q["xy"]
        if any(a + 1e-8 < x < c - 1e-8 and b + 1e-8 < y < d - 1e-8 for a, b, c, d in hb):
            nx = nearest_free((x, y), [(a, b, c, d) for a, b, c, d in hb], 0.0, W, H, lo=CL)
            at[q["name"]] = {"from": q["xy"], "to": nx}
    if at: wtap[tn] = {"clock.added_taps": at}
    rep[tn] = dict(stations_changed=srep, taps=at)
    print(tn, "stations changed", len(srep), "max hop after", max([r["max_hop_after"] for r in srep] or [0]), "taps", {k: v["to"] for k, v in at.items()})
json.dump(comp, open(pre + "_companion.json", "w"), indent=1)
json.dump(wtap, open(pre + "_window_tap.json", "w"), indent=1)
json.dump(rep, open(pre + "_fixrep.json", "w"), indent=1)
