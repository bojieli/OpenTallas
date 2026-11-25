#!/usr/bin/env python3
"""ROWS_KVQC-STACK-DESTACK (KVQC-STACK lane, on ADV-STATION-STACK a938987b28; generalises ROWS_KV-OWN-PV-R2-V1NSITE 887341f510ca).

Cause: two or more DIFFERENT buses (internal_stations by conn, ft_slots by name) with a station register on one plan
point stack their FIRM banks in one landing window (OT_CLAND "no legal site" when a START / reset tap is within 10 um).
Row (structural, no cycles): at every point shared by > 1 distinct bus the first bus (sorted name) keeps the point; the
k-th further bus moves its register perpendicular to its local leg by +STEP, -STEP, +2 STEP ... (STEP 12 um), then along
the leg.  A candidate is skipped when it lies inside a hard core (+HALO), outside the outline, on another station point,
or (preferred, first pass) within 10 um of a START / reset tap site.  The first/last register of an ft slot keeps its face
(moves along the face only, inside out_window_um when given).  Station counts, lanes, fixed_cycles unchanged; every hop
stays <= max(405, its own pre-row hop).  Types with START within 10 um are processed first.  bit_sites_um shift with the reg.

usage: ROWS_KVQC-STACK-DESTACK.py PLAN_IN PLAN_OUT REPORT_JSON [TYPE ...]   (no TYPE = every soft type with a stack)
"""
import json, sys, collections, hashlib, os
sys.path.insert(0, os.environ.get("OT_DIE_PLAN_TOOLS", "tools/die_plan"))
import adv_station_stack as AS
import adv_site_collide as SC

STEP, HALO, HOP_MAX, NEAR, CLR = 12.0, 2.0, 405.0, 10.0, 4.32


def boxes(t):
    out = []
    for h in t.get("hard_cores") or []:
        (x, y), (w, hg) = h["origin_um"], h["outline_um"]
        if str(h.get("orient", "R0")) in ("R90", "R270", "MXR90", "MYR90"):
            w, hg = hg, w
        out.append((x - HALO, y - HALO, x + w + HALO, y + hg + HALO))
    return out


def inside(pt, bx):
    return any(a < pt[0] < c and b < pt[1] < d for a, b, c, d in bx)


OUTLINE = [0.0, 0.0]


def tail(s):
    """ft slot: Manhattan distance from the last register to its out face (window when given)"""
    W, H = OUTLINE
    f, r, ow = s.get("out_face"), s["regs_um"][-1], s.get("out_window_um")
    if f not in ("N", "S", "E", "W"):
        return 0.0
    if f in ("N", "S"):
        d, v, lim = (H - r[1] if f == "N" else r[1]), r[0], ow
    else:
        d, v, lim = (W - r[0] if f == "E" else r[0]), r[1], ow
    if lim:
        v = 0.0 if lim[0] <= v <= lim[1] else min(abs(v - lim[0]), abs(v - lim[1]))
    else:
        v = 0.0
    return abs(d) + v


def hops(s):
    pts = [list(s["from_um"])] if s.get("from_um") else []
    pts += [list(r) for r in s["regs_um"]]
    if s.get("to_um"):
        pts.append(list(s["to_um"]))
    h = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])] or [0.0]
    if s.get("out_face") and not s.get("to_um"):
        h.append(tail(s))
    return h


def pk(r):
    return AS._key(r)


SW, RH = 0.054, 0.27     # core site grid (ft_bit_sites.snap_slots defaults): offsets are whole sites / rows, so moved bit sites stay on-grid


def grid_off(r, c):
    return [round(r[0] + round((c[0] - r[0]) / SW) * SW, 3), round(r[1] + round((c[1] - r[1]) / RH) * RH, 3)]


def run_type(tn, t, rep, prefer=None):
    prefer = prefer or {}
    W, H = t["outline_um"]
    OUTLINE[:] = [W, H]
    bx = boxes(t)
    items = SC.type_items(t)
    marks = [(x, y) for k, _, x, y in items if k in AS.TAP_KINDS + AS.START_KINDS]
    near = lambda c: any(abs(c[0] - a) + abs(c[1] - b) <= NEAR for a, b in marks)
    objs = []   # (bus key, obj)
    for s in t.get("internal_stations") or []:
        objs.append((str(s.get("conn")), s))
    for s in t.get("ft_slots") or []:
        objs.append((f"ft:{s.get('name')}", s))
    own = collections.defaultdict(set)
    for b, s in objs:
        for r in s["regs_um"]:
            own[pk(r)].add(b)
    rank = {k: {c: i for i, c in enumerate(sorted(v, key=lambda c: (c != prefer.get(k), c)))} for k, v in own.items() if len(v) > 1}
    grid = collections.defaultdict(list)
    for b, s in objs:
        for r in s["regs_um"]:
            grid[(int(r[0] // 8), int(r[1] // 8))].append((b, r[0], r[1]))
    taken = set(own)
    sites = collections.Counter()
    for _b, _s in objs:
        for st in _s.get("bit_sites_um") or []:
            for q in st:
                sites[(round(q[0], 3), round(q[1], 3))] += 1
    in_core0 = lambda q: any(a < q[0] < c and b < q[1] < d for a, b, c, d in boxes0)
    boxes0 = [(a + HALO, b + HALO, c - HALO, d - HALO) for a, b, c, d in bx]    # core boxes without the reg halo

    def sites_ok(s, j, dx, dy):
        bs = s.get("bit_sites_um")
        if not (isinstance(bs, list) and j < len(bs) and isinstance(bs[j], list)):
            return True
        old = {(round(q[0], 3), round(q[1], 3)) for q in bs[j]}
        for q in bs[j]:
            n = [round(q[0] + dx, 3), round(q[1] + dy, 3)]
            if not (0 <= n[0] <= W and 0 <= n[1] <= H) or (in_core0(n) and not in_core0(q)):
                return False
            if (n[0], n[1]) not in old and sites.get((n[0], n[1]), 0):
                return False
        return True

    def clear(c, b):
        gx, gy = int(c[0] // 8), int(c[1] // 8)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for ob, x, y in grid.get((gx + dx, gy + dy), ()):
                    if ob != b and abs(x - c[0]) < CLR and abs(y - c[1]) < CLR:
                        return False
        return True

    # START-near points first
    order = sorted(range(len(objs)), key=lambda i: -sum(1 for r in objs[i][1]["regs_um"] if pk(r) in rank and near(r)))
    moved, refused, mh_b, mh_a, strict, loose = 0, [], 0.0, 0.0, 0, 0
    for i in order:
        b, s = objs[i]
        hb = max(hops(s))
        mh_b = max(mh_b, hb)
        regs = [list(r) for r in s["regs_um"]]
        isft = b.startswith("ft:")
        for j, r in enumerate(regs):
            n = rank.get(pk(r), {}).get(b, 0)
            if n == 0:
                continue
            a = regs[j - 1] if j > 0 else (s.get("from_um") or None)
            c2 = regs[j + 1] if j + 1 < len(regs) else (s.get("to_um") or None)
            if a is None: a = c2
            if c2 is None: c2 = a
            if a is None or c2 is None:
                refused.append([b, r, "no leg"]); continue
            horiz = abs(c2[0] - a[0]) >= abs(c2[1] - a[1])
            end = isft and (r[0] in (0.0, W) or r[1] in (0.0, H) or abs(r[0] - W) < 1e-6 or abs(r[1] - H) < 1e-6)
            cands = []
            for m in range(n, n + 12):
                off = STEP * ((m + 1) // 2) * (1 if m % 2 else -1)
                if not end:
                    cands.append([r[0], r[1] + off] if horiz else [r[0] + off, r[1]])
            for m in range(n, n + 12):
                off = STEP * ((m + 1) // 2) * (1 if m % 2 else -1)
                if end:    # keep the face: move along the face (perpendicular to the outward leg)
                    cands.append([r[0], r[1] + off] if r[0] in (0.0, W) or abs(r[0] - W) < 1e-6 else [r[0] + off, r[1]])
                else:
                    cands.append([r[0] + off, r[1]] if horiz else [r[0], r[1] + off])
            ok = None
            g2 = sorted(([r[0] + a * 6.0, r[1] + b2 * 6.0] for a in range(-8, 9) for b2 in range(-8, 9)
                         if max(abs(a), abs(b2)) >= 2 and (not end or (a == 0 if (r[0] in (0.0, W) or abs(r[0] - W) < 1e-6) else b2 == 0))),
                        key=lambda c: abs(c[0] - r[0]) + abs(c[1] - r[1]))
            g3 = sorted(([r[0] + a * 5.0, r[1] + b2 * 5.0] for a in range(-4, 5) for b2 in range(-4, 5)
                         if max(abs(a), abs(b2)) >= 1 and (not end or (a == 0 if (r[0] in (0.0, W) or abs(r[0] - W) < 1e-6) else b2 == 0))),
                        key=lambda c: abs(c[0] - r[0]) + abs(c[1] - r[1]))   # last resort: >= 5 um (> 4.32-um window) where hops sit at the 405 cap
            for pas in (0, 1, 2, 3):
                for c in (g3 if pas == 3 else g2 if pas == 2 else cands):
                    c = grid_off(r, c)
                    if not (0 <= c[0] <= W and 0 <= c[1] <= H) or inside(c, bx) or pk(c) in taken or c == r:
                        continue
                    if not sites_ok(s, j, c[0] - r[0], c[1] - r[1]):
                        continue
                    if (pas == 0 and near(c)) or (pas != 1 and not clear(c, b)):
                        continue
                    trial = dict(s, regs_um=regs[:j] + [c] + regs[j + 1:])
                    if max(hops(trial)) > max(HOP_MAX, hb) + 1e-6:
                        continue
                    ok = c
                    strict += pas == 0
                    loose += pas >= 1
                    break
                if ok:
                    break
            if ok is None:
                refused.append([b, r, "no legal candidate"])
                continue
            dx, dy = ok[0] - r[0], ok[1] - r[1]
            regs[j] = [round(ok[0], 3), round(ok[1], 3)]
            taken.add(pk(ok))
            grid[(int(ok[0] // 8), int(ok[1] // 8))].append((b, ok[0], ok[1]))
            bs = s.get("bit_sites_um")
            if isinstance(bs, list) and j < len(bs) and isinstance(bs[j], list):
                for q in bs[j]:
                    sites[(round(q[0], 3), round(q[1], 3))] -= 1
                bs[j] = [[round(q[0] + dx, 3), round(q[1] + dy, 3)] for q in bs[j]]
                for q in bs[j]:
                    sites[(q[0], q[1])] += 1
            moved += 1
        s["regs_um"] = regs
        mh_a = max(mh_a, max(hops(s)))
    rep[tn] = dict(stacked_before=len(rank), moved=moved, strict_pass=strict, loose_pass=loose, refused=refused,
                   max_hop_before=round(mh_b, 1), max_hop_after=round(mh_a, 1))


def main():
    pin, pout, rp = sys.argv[1:4]
    only = set(sys.argv[4:])
    p = json.load(open(pin))
    rep = dict(row="ROWS_KVQC-STACK-DESTACK", plan_in_sha=hashlib.sha256(open(pin, "rb").read()).hexdigest()[:12], types={})
    for tn, t in sorted(p["partition_types"].items()):
        if not isinstance(t, dict) or t.get("hard") or (only and tn not in only):
            continue
        if AS.stacks(t):
            import copy
            t0 = copy.deepcopy(t)
            run_type(tn, t, rep["types"])
            if rep["types"][tn]["refused"]:      # the refused bus (hops at the 405 cap) keeps the point; the other bus moves
                pref = {pk(x[1]): x[0] for x in rep["types"][tn]["refused"]}
                t.clear(); t.update(t0)
                run_type(tn, t, rep["types"], pref)
                rep["types"][tn]["retry_keeper"] = sorted(set(pref.values()))
    bad = {k: v["refused"] for k, v in rep["types"].items() if v["refused"]}
    for tn, v in rep["types"].items():
        print("DESTACK", tn, json.dumps({k: x for k, x in v.items() if k != "refused"}), "refused", len(v["refused"]))
    if bad:
        json.dump(rep, open(rp, "w"), indent=1)
        print("DESTACK REFUSE", sum(map(len, bad.values())), list(bad)[:5]); raise SystemExit(3)
    json.dump(p, open(pout, "w"), indent=1)
    rep["plan_out_sha"] = hashlib.sha256(open(pout, "rb").read()).hexdigest()[:12]
    json.dump(rep, open(rp, "w"), indent=1)
    print("DESTACK plan_out", rep["plan_out_sha"])


if __name__ == "__main__":
    main()
