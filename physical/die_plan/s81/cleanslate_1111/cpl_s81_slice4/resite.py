#!/usr/bin/env python3
"""CPL-S81-SLICE-4: re-site internal-station regs (positions only, same count) so that no station hop crosses an
unrelated hard core that it did not cross in the base plan (explorer Builder._crosses test, 0.5-um shrink), and every
hop stays <= REACH Manhattan.  A straight hop that crosses no core interior has a monotone staircase route of the same
Manhattan length, so 'no new crossing + Manhattan <= reach' = routed hop <= reach.
usage (from repo/tools/die_plan): resite.py BASE_PLAN AFTER_PLAN COMPANION_IN COMPANION_OUT REPORT"""
import json, sys, copy
sys.path.insert(0, ".")
from placement_obstacles import placement_boxes
base, after, cin, cout, repp = sys.argv[1:6]
PB = json.load(open(base))["partition_types"]; PA = json.load(open(after))["partition_types"]
COMP = json.load(open(cin))
REACH, L, STEP = 405.0, 4.32, 8.64


def crosses(r, a, b):
    x0, y0, x1, y1 = r[0] + .5, r[1] + .5, r[2] - .5, r[3] - .5
    dx, dy = b[0] - a[0], b[1] - a[1]; t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0: return False
        else:
            t = q / p
            if p < 0:
                if t > t1: return False
                t0 = max(t0, t)
            else:
                if t < t0: return False
                t1 = min(t1, t)
    return t0 < t1


def inside(r, q): return r[0] <= q[0] <= r[2] and r[1] <= q[1] <= r[3]


def man(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])


def cores(t): return {h["inst"]: (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
                                  h["origin_um"][1] + h["outline_um"][1]) for h in t["hard_cores"]}


def own(s, C):
    o = set()
    for k in ("launch", "capture"):
        v = s.get(k) or ""
        o |= {i for i in C if v == i or v.startswith(i + ".")}
    return o


def xset(chain, C, ow):
    ends = [chain[0], chain[-1]]
    out = set()
    for a, b in zip(chain, chain[1:]):
        for i, r in C.items():
            if i in ow or any(inside(r, q) for q in ends): continue
            if crosses(r, a, b): out.add(i)
    return out


def hopx(a, b, C, ow, ends):
    return {i for i, r in C.items() if i not in ow and not any(inside(r, q) for q in ends) and crosses(r, a, b)}


out, rep = COMP, {}
for tn, comp in COMP.items():
    tb, ta = PB[tn], copy.deepcopy(PA[tn]); W, H = ta["outline_um"][:2]
    Cb, Ca = cores(tb), cores(ta)
    boxes = list(placement_boxes(ta).values())
    free = lambda p: 0 <= p[0] <= W and 0 <= p[1] <= H and not any(a - L < p[0] < c + L and b - L < p[1] < d + L for a, b, c, d in boxes)
    sites = [(round(i * STEP, 3), round(j * STEP, 3)) for i in range(int(W // STEP) + 1) for j in range(int(H // STEP) + 1)]
    sites = [p for p in sites if free(p)]
    bmap = {s.get("conn"): s for s in tb.get("internal_stations") or []}
    rep[tn] = []
    for k, s in enumerate(ta.get("internal_stations") or []):
        c = comp["internal_stations"][k]
        assert c["from_um"] == s["from_um"] and c["to_um"] == s["to_um"] and c["regs_um"] == s["regs_um"], (tn, k)
        s0 = bmap.get(s.get("conn"))
        ow_b, ow_a = own(s, Cb), own(s, Ca)
        allow = xset([s0["from_um"]] + s0["regs_um"] + [s0["to_um"]], Cb, ow_b) if s0 else set()
        regs = [list(r) for r in s["regs_um"]]
        chain = [s["from_um"]] + regs + [s["to_um"]]
        ends = [chain[0], chain[-1]]
        new0 = xset(chain, Ca, ow_a) - allow
        mh0 = max(man(a, b) for a, b in zip(chain, chain[1:]))
        if not new0 and mh0 <= REACH:
            continue

        def score(ch):
            nx = sum(len(hopx(a, b, Ca, ow_a, ends) - allow) for a, b in zip(ch, ch[1:]))
            mh = max(man(a, b) for a, b in zip(ch, ch[1:]))
            return (nx, max(0.0, mh - REACH), round(mh / 25), sum(man(p, q) for p, q in zip(ch[1:-1], chain[1:-1])))
        best = score(chain); cur = [list(p) for p in chain]
        for _ in range(4):
            changed = False
            for j in range(1, len(cur) - 1):
                a, b = cur[j - 1], cur[j + 1]
                for q in sites:
                    if man(q, a) > REACH or man(q, b) > REACH: continue
                    trial = cur[:j] + [list(q)] + cur[j + 1:]
                    sc = score(trial)
                    if sc < best: best, cur, changed = sc, trial, True
            if not changed: break
        c["regs_um"] = [[round(p[0], 3), round(p[1], 3)] for p in cur[1:-1]]
        rep[tn].append(dict(conn=s.get("conn"), new_cross_before=sorted(new0), maxhop_before=round(mh0, 1),
                            new_cross_after=best[0], maxhop_after=round(max(man(a, b) for a, b in zip(cur, cur[1:])), 1),
                            regs_before=regs, regs_after=c["regs_um"]))
    print(tn, [(r["conn"], r["new_cross_before"], r["maxhop_before"], "->", r["new_cross_after"], r["maxhop_after"]) for r in rep[tn]])
json.dump(out, open(cout, "w"), indent=1)
json.dump(rep, open(repp, "w"), indent=1)
