#!/usr/bin/env python3
"""ROWS_S81-STACK-DESTACK: de-stack internal_stations points shared by >= 2 buses (ADV-STATION-STACK) on an S81 plan.

Generalizes ROWS_KV-OWN-PV-R2-V1NSITE (887341f510ca): at every point shared by >1 distinct bus the first bus (sorted conn)
keeps the point; every further bus moves its register off by a 12-um lattice step, perpendicular to its leg first, then
along it, then the 2-D lattice (up to +-MAXK steps) -- S81 leaf types hold up to 57 nets on one point, so one axis is
not enough.  A candidate is skipped when it is outside the outline (minus 4.32 um), inside a hard core (+4.32 um halo),
within 4.32 um of any other plan point or FIRM item (reset tap, START, collector ...) or within 10 um of a reset tap /
START stage, or when it pushes a hop of that station above max(405 um, its own pre-row hop).  Station counts, lanes,
fixed_cycles and latency are unchanged; bit_sites_um of a moved register shift with it.  ft_slots stacks are left as is.

Priority: (a) points with a START within 10 um, (b) points with >= 8 buses, (c) the rest; processed in that order per type
(types: (a) first, then (b), then (c)), counts reported per tier.  A station that cannot move is left and reported
(--strict: exit 3).  Only soft types are touched (hard types skipped).

usage: rows_s81_stack.py PLAN_IN PLAN_OUT [REPORT_JSON] [--strict] [--types t1,t2]
"""
import collections
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_site_collide as SC  # noqa: E402

STEP, HALO, HOP_MAX, WIN, NEAR, MAXK, BIG = 12.0, 4.32, 405.0, 4.32, 10.0, 12, 8
FALLBACK_STEPS = (12.0, 6.0)      # 12-um lattice first; a 6-um lattice (>= one 4.32-um window) only when no 12-um site is legal
TAP_START = ("reset_tap", "reset_relay", "start", "local_reset_start")


def boxes(t):
    out = []
    for h in t.get("hard_cores") or []:
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        if str(h.get("orient", "R0")) in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        out.append((x - HALO, y - HALO, x + w + HALO, y + hh + HALO))
    return out


def hops(s, regs=None):
    pts = [s["from_um"]] + [list(r) for r in (s["regs_um"] if regs is None else regs)] + [s["to_um"]]
    return [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]


def key(r):
    return (round(r[0] / 0.1), round(r[1] / 0.1))


class Grid:
    def __init__(self):
        self.g = collections.defaultdict(list)

    def add(self, p):
        self.g[(int(p[0] // WIN), int(p[1] // WIN))].append((p[0], p[1]))

    def near(self, p, d=WIN):
        cx, cy = int(p[0] // WIN), int(p[1] // WIN)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for q in self.g.get((cx + i, cy + j), ()):
                    if abs(q[0] - p[0]) < d and abs(q[1] - p[1]) < d:
                        return True
        return False


LATTICE = sorted(((i, j) for i in range(-MAXK, MAXK + 1) for j in range(-MAXK, MAXK + 1) if i or j),
                 key=lambda a: (abs(a[0]) + abs(a[1]), max(abs(a[0]), abs(a[1])), -(a[0] > 0 or (a[0] == 0 and a[1] > 0)), a))


def plan_type(t):
    """in-place de-stack of one partition type; returns its stats dict"""
    W, H = t["outline_um"]
    bx = boxes(t)
    st = [s for s in (t.get("internal_stations") or []) if isinstance(s, dict) and s.get("regs_um")]
    items = SC.type_items(t)
    ts = [(x, y) for k, _, x, y in items if k in TAP_START]
    own = collections.defaultdict(dict)
    for s in st:
        for r in s["regs_um"]:
            q = SC._xy(r)
            if q:
                own[key(q)].setdefault(str(s["conn"]), q)
    stacked = {k: v for k, v in own.items() if len(v) > 1}
    stat = dict(points=len(stacked), moved=0, refused=[], start_pts=0, big_pts=0, max_buses=0)
    if not stacked:
        return stat
    grid = Grid()
    for _, _, x, y in items:
        grid.add((x, y))
    taken = set(own)
    for k, v in own.items():
        grid.add(next(iter(v.values())))
    # priority per point: (a) START within NEAR, (b) >= BIG buses, (c) rest
    def tier(k):
        q = next(iter(stacked[k].values()))
        if any(abs(q[0] - a) + abs(q[1] - b) <= NEAR for a, b in ts):
            return 0
        return 1 if len(stacked[k]) >= BIG else 2
    tiers = {k: tier(k) for k in stacked}
    stat["start_pts"] = sum(1 for v in tiers.values() if v == 0)
    stat["big_pts"] = sum(1 for v in tiers.values() if v <= 1)
    stat["max_buses"] = max(len(v) for v in stacked.values())
    stat["tier_points"] = [sum(1 for v in tiers.values() if v == i) for i in range(3)]
    stat["tier_moved"] = [0, 0, 0]
    rank = {k: {c: i for i, c in enumerate(sorted(v))} for k, v in stacked.items()}
    work = []                                    # (tier, -buses, key, conn, station)
    by_conn = collections.defaultdict(list)
    for s in st:
        by_conn[str(s["conn"])].append(s)
    for k in stacked:
        for c, n in rank[k].items():
            if n:
                work.append((tiers[k], -len(stacked[k]), k, n, c))
    work.sort()
    for tr, _, k, n, c in work:
        for s in by_conn[c]:
            regs = [list(r) for r in s["regs_um"]]
            hb = max(hops(s))
            for i, r in enumerate(regs):
                if key(r) != k:
                    continue
                a = regs[i - 1] if i > 0 else s["from_um"]
                b = regs[i + 1] if i + 1 < len(regs) else s["to_um"]
                horiz = abs(b[0] - a[0]) >= abs(b[1] - a[1])
                perp = [ij for ij in LATTICE if (ij[0] == 0 if horiz else ij[1] == 0)]
                ps = set(perp)
                ordered = [(i1 * stp, j1 * stp) for stp in FALLBACK_STEPS for i1, j1 in perp + [ij for ij in LATTICE if ij not in ps]]
                ok = None
                for dx, dy in ordered:
                    c2 = [r[0] + dx, r[1] + dy]
                    if not (HALO <= c2[0] <= W - HALO and HALO <= c2[1] <= H - HALO):
                        continue
                    if any(a_ < c2[0] < c_ and b_ < c2[1] < d_ for a_, b_, c_, d_ in bx):
                        continue
                    if key(c2) in taken or grid.near(c2):
                        continue
                    if any(abs(c2[0] - x) + abs(c2[1] - y) <= NEAR for x, y in ts):
                        continue
                    if max(hops(s, regs[:i] + [c2] + regs[i + 1:])) > max(HOP_MAX, hb) + 1e-6:
                        continue
                    ok = c2
                    break
                if ok is None:
                    stat["refused"].append([c, [round(r[0], 3), round(r[1], 3)]])
                    continue
                dx, dy = ok[0] - r[0], ok[1] - r[1]
                regs[i] = [round(ok[0], 3), round(ok[1], 3)]
                taken.add(key(ok))
                grid.add(ok)
                bs = s.get("bit_sites_um")
                if isinstance(bs, list) and i < len(bs) and isinstance(bs[i], list):
                    bs[i] = [[round(q[0] + dx, 3), round(q[1] + dy, 3)] for q in bs[i]]
                stat["moved"] += 1
                stat["tier_moved"][tr] += 1
            s["regs_um"] = regs
    return stat


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    strict = "--strict" in sys.argv
    only = None
    for x in sys.argv[1:]:
        if x.startswith("--types="):
            only = set(x.split("=", 1)[1].split(","))
    pin, pout = a[0], a[1]
    rep_path = a[2] if len(a) > 2 else pout + ".stack.json"
    p = json.load(open(pin))
    rep = dict(row="ROWS_S81-STACK-DESTACK", plan_in=pin, plan_in_sha=hashlib.sha256(open(pin, "rb").read()).hexdigest()[:12],
               step_um=STEP, types={})
    for tn, t in sorted(p["partition_types"].items()):
        if not isinstance(t, dict) or t.get("hard") or (only and tn not in only):
            continue
        s = plan_type(t)
        if s["points"]:
            rep["types"][tn] = s
    T = rep["types"]
    rep["summary"] = dict(
        types=len(T), points=sum(v["points"] for v in T.values()), moved_regs=sum(v["moved"] for v in T.values()),
        refused=sum(len(v["refused"]) for v in T.values()), start_points=sum(v["start_pts"] for v in T.values()),
        big_points=sum(v["big_pts"] for v in T.values()),
        tier_points=[sum(v["tier_points"][i] for v in T.values()) for i in range(3)],
        tier_moved=[sum(v["tier_moved"][i] for v in T.values()) for i in range(3)])
    if strict and rep["summary"]["refused"]:
        print("STACK REFUSE", rep["summary"])
        raise SystemExit(3)
    with open(pout, "w") as f:
        json.dump(p, f, indent=1)
        f.write("\n")
    rep["plan_out_sha"] = hashlib.sha256(open(pout, "rb").read()).hexdigest()[:12]
    json.dump(rep, open(rep_path, "w"), indent=1)
    print("STACK", json.dumps(rep["summary"]))
    print("STACK plan_out", rep["plan_out_sha"])


if __name__ == "__main__":
    main()
