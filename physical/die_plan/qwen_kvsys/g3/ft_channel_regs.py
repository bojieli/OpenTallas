#!/usr/bin/env python3
"""KV-G3 10-24 (GEOM-REVIEW batch 1, KV v3.8v): declare ft station sites (ft_slots[].regs_um) in core-free channels.

GEOM-REVIEW found 1,394 of 4,359 interpolated ft station points (station j at L*j/k on the slot's zroute, as check.py /
face_flops.tcl place them without regs_um) INSIDE hard cores (hgi_v7 252, hgi_v4 240, pv_v4 96, ...): the kit then
moves them and hops grow.  For every type with hard_cores, every ft slot station j >= 1 whose interpolated point lies in a
core box grown by CLEAR (8.64 um) moves to the nearest free point: first along the slot route (|dt| <= L/(2k)), then on
rings around it (<= RING_MAX um).  Station 0 stays at the in pin (the in face register).  regs_um is then written for
every slot of such a type that had a moved station (all k points, schema: len == stations).  Hops are re-checked: in->s1,
s_j->s_j+1, s_last->out pin (the seam hop) must stay <= ft_station_max_um, else the slot is reported and left untouched.
With --add-stations a slot whose route has no core-free fit within the limit gets stations + 1 (+1 cycle on every lane
crossing it; run gen.py latency after).
usage: ft_channel_regs.py die_plan.json [--report OUT.json] [--add-stations] > die_plan.json"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "tools/die_plan"))
import check as C       # noqa: E402
import schema as S      # noqa: E402

CLEAR = 8.64
STEP = 2.16
RING_MAX = 300.0
ADD = False   # --add-stations: a slot with no core-free fit gets one more station (+1 cycle on its lanes)


def boxes_of(t):
    out = []
    for c in t.get("hard_cores") or []:
        (ox, oy), (w, h) = c["origin_um"], c["outline_um"]
        out.append((ox - CLEAR, oy - CLEAR, ox + w + CLEAR, oy + h + CLEAR, c["inst"]))
    return out


def inside(p, bx):
    return next((b[4] for b in bx if b[0] < p[0] < b[2] and b[1] < p[1] < b[3]), None)


def free_point(seg, L, t0, span, bx, W, H):
    """nearest core-free point: along the route first, then rings (Manhattan) around the interpolated point"""
    n = int(span / STEP)
    for i in range(1, n + 1):
        for t in (t0 - i * STEP, t0 + i * STEP):
            if 0 < t < L:
                q = C.point_at(seg, t)
                if not inside(q, bx):
                    return q, "route"
    x0, y0 = C.point_at(seg, t0)
    r = STEP
    while r <= RING_MAX:
        best = None
        k = int(r / STEP)
        for i in range(-k, k + 1):
            dx = i * STEP
            for dy in (r - abs(dx), -(r - abs(dx))):
                q = (x0 + dx, y0 + dy)
                if CLEAR <= q[0] <= W - CLEAR and CLEAR <= q[1] <= H - CLEAR and not inside(q, bx):
                    best = q
                    break
            if best:
                return best, "ring"
        r += STEP
    return None, "none"


def route_fit(seg, L, k, bx, smax):
    """k-1 free points ON the route (route distance t increasing) minimising the largest gap (in->s1 .. s_last->out),
    for slots where single-station moves break the hop limit.  Returns (points, max_gap) or (None, gap)."""
    n = int(L / STEP)
    free = [i * STEP for i in range(1, n) if not inside(C.point_at(seg, i * STEP), bx)]

    def greedy(G):
        out, cur, i = [], 0.0, 0
        for _ in range(k - 1):
            best = None
            while i < len(free) and free[i] <= cur + G:
                best = free[i]
                i += 1
            if best is None:
                return None
            out.append(best)
            cur = best
            if L - cur <= G:
                break
        if L - cur > G:
            return None
        while len(out) < k - 1:          # spare stations: split the largest gap at the free point nearest its middle
            pts = [0.0] + out + [L]
            g, j = max((pts[i + 1] - pts[i], i) for i in range(len(pts) - 1))
            mid = pts[j] + g / 2
            cand = [f for f in free if pts[j] < f < pts[j + 1] and f not in out]
            if not cand:
                return None
            out = sorted(out + [min(cand, key=lambda f: abs(f - mid))])
        return out
    lo, hi = L / k, L
    if greedy(hi) is None:
        return None, float("inf")
    for _ in range(40):
        mid = (lo + hi) / 2
        if greedy(mid) is None:
            lo = mid
        else:
            hi = mid
    ts = greedy(hi)
    return [C.point_at(seg, 0.0)] + [C.point_at(seg, t) for t in ts], hi


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def main():
    pf = sys.argv[1]
    rep_f = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    global ADD
    ADD = "--add-stations" in sys.argv
    raw = json.load(open(pf))
    P = S.Plan(raw)
    smax = float(raw.get("budgets", {}).get("ft_station_max_um", 750.0))
    rep = dict(schema="opentallas.kv_g3.ft_channel_regs.v1", clear_um=CLEAR, smax_um=smax, types={})
    tot = dict(points=0, in_core=0, moved=0, failed=0)
    for tn, t in raw["partition_types"].items():
        bx = boxes_of(t)
        if not bx or not t.get("ft_slots"):
            continue
        W, H = t["outline_um"]
        bt = C._bus_targets(P, tn)
        r = dict(points=0, in_core=0, moved=0, failed=[], max_shift_um=0.0, max_hop_before=0.0, max_hop_after=0.0)
        for s in t["ft_slots"]:
            a, b = bt.get(s["name"] + "_i"), bt.get(s["name"] + "_o")
            if not a or not b:
                continue
            seg = C.zroute(a[1], b[1], s.get("in_face", "W"), s.get("out_face", "E"))
            L = C.plen(seg)
            k = int(s.get("stations", 1))
            st = [tuple(x) for x in s["regs_um"]] if s.get("regs_um") else [C.point_at(seg, L * j / k) for j in range(k)]
            new = list(st)
            hit = False
            for j in range(1, k):
                r["points"] += 1
                if not inside(st[j], bx):
                    continue
                r["in_core"] += 1
                q, how = free_point(seg, L, L * j / k, L / (2 * k), bx, W, H)
                if q is None:
                    r["failed"].append(f"{s['name']}.s{j}: no free point")
                    continue
                r["max_shift_um"] = max(r["max_shift_um"], man(q, st[j]))
                new[j] = (round(q[0], 3), round(q[1], 3))
                hit = True
            hb = max(man(p, q) for p, q in zip(st + [b[1]], st[1:] + [b[1]]))
            ha = max(man(p, q) for p, q in zip(new + [b[1]], new[1:] + [b[1]]))
            r["max_hop_before"] = max(r["max_hop_before"], hb)
            if not hit:
                r["max_hop_after"] = max(r["max_hop_after"], hb)
                continue
            if ha > smax:
                fit, g = route_fit(seg, L, k, bx, smax)
                if fit is not None:
                    new = [(round(q[0], 3), round(q[1], 3)) for q in fit]
                    ha = max(man(p, q) for p, q in zip(new + [b[1]], new[1:] + [b[1]]))
                if (fit is None or ha > smax) and ADD:
                    fit, g = route_fit(seg, L, k + 1, bx, smax)
                    if fit is not None:
                        new = [(round(q[0], 3), round(q[1], 3)) for q in fit]
                        ha = max(man(p, q) for p, q in zip(new + [b[1]], new[1:] + [b[1]]))
                        if ha <= smax:
                            s["stations"] = k + 1
                            r.setdefault("added_station", []).append(s["name"])
                if (fit is None or ha > smax) and s.get("stations", 1) == k:
                    r["failed"].append(f"{s['name']}: hop {ha:.0f} > {smax:g} after the move and no on-route fit "
                                       f"(best gap {g:.0f}; left interpolated: needs a station or a channel route)")
                    r["max_hop_after"] = max(r["max_hop_after"], hb)
                    continue
            r["max_hop_after"] = max(r["max_hop_after"], ha)
            r["moved"] += sum(1 for p, q in zip(st, new) if p != q)
            s["regs_um"] = [[round(p[0], 3), round(p[1], 3)] for p in new]
        for kk in ("points", "in_core", "moved"):
            tot[kk] += r[kk]
        tot["failed"] += len(r["failed"])
        r["max_shift_um"] = round(r["max_shift_um"], 1)
        r["max_hop_before"] = round(r["max_hop_before"], 1)
        r["max_hop_after"] = round(r["max_hop_after"], 1)
        rep["types"][tn] = r
    rep["total"] = tot
    sys.stderr.write(f"ft_channel_regs: {json.dumps(tot)}\n")
    if rep_f:
        Path(rep_f).write_text(json.dumps(rep, indent=1))
    raw["note"] = raw.get("note", "") + (f" | ft_channel_regs (KV-G3): {tot['moved']} ft stations moved off hard cores "
                                         "into channels (declared regs_um)")
    json.dump(raw, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
