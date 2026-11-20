#!/usr/bin/env python3
"""S81-HI-CORRIDOR (FABLE-FIX-S81-LEAF 11-19, COORD lever 5): vp HI-quad buses over the lane hard cores.

The leaf RTL shares the first CS_HI_GS (2) hi station stages per quad (lanes 4g..4g+3, CS_H_G 4): one 1,0xx-flop bank
per quad stage.  kit_istations places each shared bank at the bit-weighted centroid of its member lanes' plan sites,
and that centroid often lands INSIDE a lane / vn core (t28 4/8, t31 5/8 shared banks), so the placer splits the bank to
both sides and the bus crosses the core twice (measured t28/t27 GRT hot gcells: cap 5-8 over lane boxes, usage 7-12).

  check PLAN [--types RE] [--json OUT]      estimator (PRECHECK): per shared bank: site inside a core?; per hard core:
                                            HI bus bits crossing it vs over-core tracks (extent x TRK tracks/um)
  seed  PLAN --types RE --form A|B --out SEED.json [--corridor 30.24]
        A = corridor: keep the lane -> quad map, widen every lane column / row gap below --corridor to --corridor
        B = remap: keep the 16 lane sites, give each quad 4 sites in one lane column (nearest the vn face first)
        (SEED = core_place.py --seed input {type: {inst: {origin_um, orient}}})
  apply PLAN --seed SEED.json --out PLAN_OUT  rigid lane moves with their riding coordinates (clock / landing records,
                                            station end points, per-lane registers near the lane); then
                                            istation_clear.py / leaf_slot_clear.py, then `sites`
  sites PLAN --types RE --out PLAN_OUT      every shared bank gets ONE explicit site in a free channel (all member
                                            lanes' regs_um[j] = that point): s0 nearest free point to the old centroid,
                                            s1 the free point with the least max hop to the members' next points.
                                            Station counts, cycles, bits, pins unchanged; hops <= max(400, before).
"""
import argparse, itertools, json, re, sys
from collections import defaultdict

LN = re.compile(r"g_ln\[(\d+)\]\.u_l$")
TRK = 10.0          # measured over-core tracks/um per direction (t28 GRT gcell 0.57 um: H cap 5-8, V cap 6)
LIMIT = 400.0
G = 4.32
SEP = 21.6         # um between two shared banks
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])          # noqa: E731
snap = lambda v: round(round(v / G) * G, 3)                      # noqa: E731


def boxes(t):
    out = []
    for h in t["hard_cores"]:
        w, hh = h["outline_um"]
        if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        x, y = h["origin_um"]
        out.append((h["inst"], x, y, x + w, y + hh))
    return out


def clear(p, B):
    """distance from p to the nearest core box (0 inside)"""
    d = 1e9
    for _, x0, y0, x1, y1 in B:
        dx = max(x0 - p[0], 0, p[0] - x1); dy = max(y0 - p[1], 0, p[1] - y1)
        d = min(d, (dx * dx + dy * dy) ** 0.5)
    return d


def hi_rows(t):
    """quad -> stage j -> [entry] for the vn -> lane (hi) rows"""
    q = defaultdict(list)
    for e in t.get("internal_stations") or []:
        m = LN.search(e.get("capture", ""))
        if m and "u_vn" in e.get("launch", "") and e.get("regs_um"):
            q[int(m[1]) // 4].append(e)
    return q


def centroid(es, j):
    es = [e for e in es if len(e["regs_um"]) > j]
    w = sum(e["bits"] for e in es)
    return (sum(e["regs_um"][j][0] * e["bits"] for e in es) / w, sum(e["regs_um"][j][1] * e["bits"] for e in es) / w) if w else None


def lane_bits(es):
    by = defaultdict(int)
    for e in es:
        by[e["capture"]] += e["bits"]
    return max(by.values()) if by else 0


def nxt(e, j):
    return e["regs_um"][j + 1] if len(e["regs_um"]) > j + 1 else e["to_um"]


def legs(a, b):
    """two L paths a->b (x first / y first) as segment lists"""
    c1, c2 = (b[0], a[1]), (a[0], b[1])
    return [[(a, c1), (c1, b)], [(a, c2), (c2, b)]]


def crossing(seg, box):
    """(direction, um of the segment inside the box, box extent across the segment)"""
    (x0, y0), (x1, y1) = seg; _, bx0, by0, bx1, by1 = box
    if abs(y0 - y1) < 1e-6 and by0 < y0 < by1:
        o = min(max(x0, x1), bx1) - max(min(x0, x1), bx0)
        return ("H", o, by1 - by0) if o > 0 else None
    if abs(x0 - x1) < 1e-6 and bx0 < x0 < bx1:
        o = min(max(y0, y1), by1) - max(min(y0, y1), by0)
        return ("V", o, bx1 - bx0) if o > 0 else None
    return None


def check(P, rex, gs):
    rep = {}
    for tn, t in sorted(P["partition_types"].items()):
        if not re.search(rex, tn):
            continue
        B = boxes(t); Q = hi_rows(t)
        if not Q:
            continue
        banks, load = [], defaultdict(lambda: dict(H=0, V=0))
        for g, es in sorted(Q.items()):
            bits = lane_bits(es)
            for j in range(gs):
                c = centroid(es, j)
                if c is None:
                    continue
                ins = [b[0] for b in B if b[1] < c[0] < b[3] and b[2] < c[1] < b[4]]
                banks.append(dict(quad=g, stage=j, site=[round(c[0], 2), round(c[1], 2)], inside=ins, clear_um=round(clear(c, B), 1)))
                # bus legs: shared bank j -> next point of every member (j < gs-1: next shared bank; else each lane)
                if j < gs - 1:
                    targets = [centroid(es, j + 1)]
                else:
                    targets = list({tuple(nxt(e, j)) for e in es if len(e["regs_um"]) > j})
                for tg in targets:
                    if tg is None:
                        continue
                    best = min(legs(c, tg), key=lambda L: sum(1 for s in L for b in B if crossing(s, b)))
                    for s in best:
                        for b in B:
                            x = crossing(s, b)
                            if x:
                                load[b[0]][x[0]] += bits
                                load[b[0]]["ext_" + x[0]] = round(x[2], 1)
        cores = {}
        for k, v in load.items():
            for d in "HV":
                if v[d]:
                    sup = v["ext_" + d] * TRK
                    cores.setdefault(k, {})[d] = dict(bits=v[d], tracks=round(sup), ratio=round(v[d] / sup, 2))
        worst = max([c[d]["ratio"] for c in cores.values() for d in c] or [0])
        n_in = sum(1 for b in banks if b["inside"])
        rep[tn] = dict(banks_inside_core=n_in, banks=len(banks), worst_ratio=worst,
                       verdict="OVER" if worst > 1 or n_in else ("RISK" if worst > 0.5 else "OK"), bank_sites=banks, cores=cores)
    return rep


def free_points(t, B, mincl, step=4.32):
    W, H = t["outline_um"]
    pts = []
    y = step
    while y < H - step:
        x = step
        while x < W - step:
            c = clear((x, y), B)
            if c >= mincl:
                pts.append(((round(x, 3), round(y, 3)), c))
            x += step
        y += step
    return pts


def sites(P, rex, gs, mincl):
    rows = []
    for tn, t in sorted(P["partition_types"].items()):
        if not re.search(rex, tn):
            continue
        Q = hi_rows(t)
        if not Q:
            continue
        B = boxes(t)
        FP = free_points(t, B, mincl)
        if not FP:
            rows.append(dict(type=tn, result="no free point")); continue
        used = []          # banks already sited in this type: keep >= SEP um apart (one bank per channel spot)
        hop0 = {id(e): max(md(a, b) for a, b in zip([e["from_um"]] + e["regs_um"], e["regs_um"] + [e["to_um"]]))
                for es in Q.values() for e in es}
        for g, es in sorted(Q.items()):
            prev = None
            for j in range(gs):
                mem = [e for e in es if len(e["regs_um"]) > j]
                if not mem:
                    continue
                c = centroid(mem, j)
                before = max(max(md(a, b) for a, b in zip([e["from_um"]] + e["regs_um"], e["regs_um"] + [e["to_um"]])) for e in mem)
                lim = max(LIMIT, before)

                def worst(p):
                    w = 0
                    for e in mem:
                        a = prev if prev is not None else (e["regs_um"][j - 1] if j else e["from_um"])
                        w = max(w, md(a, p), md(p, nxt(e, j)) if j == gs - 1 else 0)
                    return w
                FPu = [q for q in FP if md(q[0], c) <= 2 * LIMIT and all(md(q[0], u) >= SEP for u in used)]
                if j == 0:
                    cand = sorted(FPu, key=lambda q: md(q[0], c))[:400]
                    cand = [q for q in cand if worst(q[0]) <= lim]
                    pick = cand[0][0] if cand else None
                else:
                    cand = [(worst(q[0]), -q[1], q[0]) for q in FPu]
                    cand = [q for q in cand if q[0] <= lim]
                    pick = min(cand)[2] if cand else None
                if pick is None:
                    rows.append(dict(type=tn, quad=g, stage=j, result="REFUSED no site within hop limit", lim=lim)); prev = None; continue
                for e in mem:
                    e["regs_um"][j] = [pick[0], pick[1]]
                    e["note"] = e.get("note", "") + f" | S81-HI-CORRIDOR shared quad{g} stage {j} site {pick[0]},{pick[1]} (was centroid {c[0]:.1f},{c[1]:.1f})"
                after = max(max(md(a, b) for a, b in zip([e["from_um"]] + e["regs_um"], e["regs_um"] + [e["to_um"]])) for e in mem)
                rows.append(dict(type=tn, quad=g, stage=j, result="sited", old=[round(c[0], 2), round(c[1], 2)], new=pick,
                                 clear_um=round(clear(pick, B), 1), max_hop_before=round(before, 1), max_hop_after=round(after, 1)))
                prev = pick
                used.append(pick)
        for es in Q.values():          # final hop check over the whole rows (both stages moved)
            for e in es:
                h = max(md(a, b) for a, b in zip([e["from_um"]] + e["regs_um"], e["regs_um"] + [e["to_um"]]))
                if h > max(LIMIT, hop0[id(e)]) + 1e-6:
                    rows.append(dict(type=tn, capture=e["capture"], result="REFUSED final hop", hop=round(h, 1),
                                     before=round(hop0[id(e)], 1)))
    return rows


def lanes_of(t):
    L = {}
    for h in t["hard_cores"]:
        m = LN.search(h["inst"])
        if m:
            L[int(m[1])] = h
    return L


def vn_face(t):
    va = [h for h in t["hard_cores"] if h["inst"].endswith("u_vn.u_a")][0]
    w, hh = va["outline_um"]
    o = va.get("orient", "R0")
    fx = va["origin_um"][0] + (w if o in ("MY", "R180") else 0)
    return fx, va["origin_um"][1] + hh / 2


def columns(L, tol=30.0):
    xs = sorted(L.items(), key=lambda kv: kv[1]["origin_um"][0])
    cols = []
    for k, h in xs:
        if cols and h["origin_um"][0] - cols[-1][-1][1]["origin_um"][0] <= tol:
            cols[-1].append((k, h))
        else:
            cols.append([(k, h)])
    return cols


def seed(P, rex, form, cor):
    out, rep = {}, {}
    for tn, t in sorted(P["partition_types"].items()):
        if not re.search(rex, tn):
            continue
        L = lanes_of(t)
        if len(L) != 16:
            continue
        lw, lh = L[0]["outline_um"]
        fx, fy = vn_face(t)
        cols = columns(L)
        sd = {}
        if form == "A":
            # pairwise relaxation: two lanes facing each other across a gap < cor (overlapping in the other axis) ->
            # the lane farther from the vn face (along that axis) moves away by the deficit; repeat to a fixpoint
            pos = {k: list(h["origin_um"]) for k, h in L.items()}
            for _ in range(200):
                moved = False
                for i, j in itertools.combinations(sorted(pos), 2):
                    a_, b_ = pos[i], pos[j]
                    ox = min(a_[0], b_[0]) + lw - max(a_[0], b_[0])      # x overlap (>0: stacked in y)
                    oy = min(a_[1], b_[1]) + lh - max(a_[1], b_[1])
                    if ox > 0 and oy <= 0:
                        lo_, hi_ = (i, j) if a_[1] < b_[1] else (j, i)
                        gap = pos[hi_][1] - pos[lo_][1] - lh
                        if gap < cor - 1e-6:
                            far = hi_ if abs(pos[hi_][1] + lh / 2 - fy) >= abs(pos[lo_][1] + lh / 2 - fy) else lo_
                            pos[far][1] = snap(pos[far][1] + (cor - gap + G / 2) * (1 if far == hi_ else -1)); moved = True
                    elif oy > 0 and ox <= 0:
                        lo_, hi_ = (i, j) if a_[0] < b_[0] else (j, i)
                        gap = pos[hi_][0] - pos[lo_][0] - lw
                        if gap < cor - 1e-6:
                            far = hi_ if abs(pos[hi_][0] + lw / 2 - fx) >= abs(pos[lo_][0] + lw / 2 - fx) else lo_
                            pos[far][0] = snap(pos[far][0] + (cor - gap + G / 2) * (1 if far == hi_ else -1)); moved = True
                if not moved:
                    break
            for k, h in L.items():
                sd[h["inst"]] = dict(origin_um=pos[k], orient=h.get("orient", "R0"))
            W, H = t["outline_um"]
            span = [min(p[0] for p in pos.values()), min(p[1] for p in pos.values()), max(p[0] for p in pos.values()) + lw, max(p[1] for p in pos.values()) + lh]
            rep[tn] = dict(form="A", lane_bbox=[round(v, 2) for v in span], inside_outline=span[0] >= 0 and span[1] >= 0 and span[2] <= W and span[3] <= H)
        else:
            Qe = hi_rows(t)
            pin_c = {}
            for g, es in Qe.items():
                w = sum(e["bits"] for e in es)
                pin_c[g] = (sum(e["from_um"][0] * e["bits"] for e in es) / w, sum(e["from_um"][1] * e["bits"] for e in es) / w)
            cs = sorted(cols, key=lambda c: abs(sum(h["origin_um"][0] for _, h in c) / len(c) + lw / 2 - fx))
            chunks, left = [], []
            for c in cs:
                s = sorted(c, key=lambda kv: kv[1]["origin_um"][1])
                while len(s) >= 4:          # the 4 consecutive sites nearest the vn centre y
                    i = min(range(len(s) - 3), key=lambda i: abs(sum(h["origin_um"][1] for _, h in s[i:i + 4]) / 4 + lh / 2 - fy))
                    chunks.append(s[i:i + 4]); s = s[:i] + s[i + 4:]
                left += s
            left.sort(key=lambda kv: md(kv[1]["origin_um"], (fx, fy)))
            while len(left) >= 4:
                chunks.append(left[:4]); left = left[4:]
            chunks = chunks[:4]
            cen = lambda ch: (sum(h["origin_um"][0] for _, h in ch) / 4 + lw / 2, sum(h["origin_um"][1] for _, h in ch) / 4 + lh / 2)  # noqa
            best = min(itertools.permutations(range(4)), key=lambda p: sum(md(pin_c.get(g, (fx, fy)), cen(chunks[p[g]])) for g in range(4)))
            for g in range(4):
                ch = chunks[best[g]]
                lanes = list(range(4 * g, 4 * g + 4))
                lp = {}
                for l in lanes:
                    es = [e for e in Qe.get(g, []) if LN.search(e["capture"])[1] == str(l)]
                    w = sum(e["bits"] for e in es) or 1
                    lp[l] = (sum(e["from_um"][0] * e["bits"] for e in es) / w, sum(e["from_um"][1] * e["bits"] for e in es) / w) if es else (fx, fy)
                perm = min(itertools.permutations(range(4)), key=lambda p: sum(md(lp[l], ch[p[i]][1]["origin_um"]) for i, l in enumerate(lanes)))
                for i, l in enumerate(lanes):
                    site = ch[perm[i]][1]
                    sd[L[l]["inst"]] = dict(origin_um=list(site["origin_um"]), orient=L[l].get("orient", "R0"))
            pure = sum(1 for ch in chunks if max(h["origin_um"][0] for _, h in ch) - min(h["origin_um"][0] for _, h in ch) <= 30)
            moved = sum(1 for k, h in L.items() if sd[h["inst"]]["origin_um"] != list(h["origin_um"]))
            rep[tn] = dict(form="B", quads_in_one_column=pure, lanes_moved=moved)
        out[tn] = sd
    return out, rep


def _shift(v, d):
    return [round(v[0] + d[0], 4), round(v[1] + d[1], 4)] + list(v[2:])


def move_lanes(t, sd, gs, near=30.0):
    """rigid lane moves (same orient): the lane, every clock / landing record of that lane (inst / name prefix),
    the end points of station rows on it, and the registers of those rows near the old lane box (hi rows: the
    per-lane stages >= gs only; the shared banks are re-sited by `sites`) move by the lane's delta."""
    L = {h["inst"]: h for h in t["hard_cores"] if LN.search(h["inst"])}
    D, old = {}, {}
    for inst, v in sd.items():
        h = L[inst]
        if v.get("orient", h.get("orient", "R0")) != h.get("orient", "R0"):
            raise SystemExit(f"HI_CORRIDOR_APPLY refuses an orient change on {inst}")
        d = (v["origin_um"][0] - h["origin_um"][0], v["origin_um"][1] - h["origin_um"][1])
        if abs(d[0]) + abs(d[1]) > 1e-6:
            w, hh = h["outline_um"]
            old[inst] = (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + w, h["origin_um"][1] + hh)
            D[inst] = d
            h["origin_um"] = [round(v["origin_um"][0], 4), round(v["origin_um"][1], 4)]
    n = dict(lanes=len(D), clock=0, ends=0, regs=0)

    def walk(o):
        if isinstance(o, dict):
            inst = o.get("inst") if o.get("inst") in D else next((k for k in D if str(o.get("name", "")).startswith(k + ".")), None)
            if inst:
                for k in ("xy", "pin_um", "tap_um"):
                    if isinstance(o.get(k), list) and len(o[k]) >= 2 and all(isinstance(x, (int, float)) for x in o[k][:2]):
                        o[k] = _shift(o[k], D[inst]); n["clock"] += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(t.get("clock") or {})
    for e in t.get("internal_stations") or []:
        for inst, d in D.items():
            cap = e.get("capture") == inst
            lau = e.get("launch", "").startswith("core:" + inst + ".")
            if not (cap or lau):
                continue
            if cap:
                e["to_um"] = _shift(e["to_um"], d); n["ends"] += 1
            if lau:
                e["from_um"] = _shift(e["from_um"], d); n["ends"] += 1
            hi = cap and "u_vn" in e.get("launch", "")
            b = old[inst]
            for j, r in enumerate(e.get("regs_um") or []):
                if hi and j < gs:
                    continue
                dx = max(b[0] - r[0], 0, r[0] - b[2]); dy = max(b[1] - r[1], 0, r[1] - b[3])
                if max(dx, dy) <= near:
                    e["regs_um"][j] = _shift(r, d); n["regs"] += 1
            e["note"] = e.get("note", "") + f" | S81-HI-CORRIDOR lane move {inst} by {d[0]:.2f},{d[1]:.2f}"
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("check", "seed", "sites", "apply"))
    ap.add_argument("--seed")
    ap.add_argument("plan")
    ap.add_argument("--types", default=r"ot_s81sl_leaf__t\d+")
    ap.add_argument("--gs", type=int, default=2)
    ap.add_argument("--form", choices=("A", "B"))
    ap.add_argument("--corridor", type=float, default=30.24)
    ap.add_argument("--min-clear", type=float, default=8.64)
    ap.add_argument("--out"); ap.add_argument("--json")
    a = ap.parse_args()
    P = json.load(open(a.plan))
    if a.cmd == "check":
        rep = check(P, a.types, a.gs)
        for tn, r in rep.items():
            print(tn, r["verdict"], "banks_inside_core", f"{r['banks_inside_core']}/{r['banks']}", "worst_bits_per_track", r["worst_ratio"])
        if a.json:
            json.dump(rep, open(a.json, "w"), indent=1)
        print("HI_CORRIDOR_CHECK", {v: sum(1 for r in rep.values() if r["verdict"] == v) for v in ("OK", "RISK", "OVER")})
    elif a.cmd == "seed":
        sd, rep = seed(P, a.types, a.form, a.corridor)
        json.dump(sd, open(a.out, "w"), indent=1)
        for tn, r in rep.items():
            print(tn, r)
    elif a.cmd == "apply":
        S = json.load(open(a.seed))
        for tn, sd in S.items():
            if re.search(a.types, tn):
                print(tn, "HI_CORRIDOR_APPLY", move_lanes(P["partition_types"][tn], sd, a.gs))
        json.dump(P, open(a.out, "w"), indent=1)
    else:
        rows = sites(P, a.types, a.gs, a.min_clear)
        json.dump(P, open(a.out, "w"), indent=1)
        json.dump(rows, open(a.out + ".sites.json", "w"), indent=1)
        bad = [r for r in rows if r["result"] != "sited"]
        print("HI_CORRIDOR_SITES", len(rows) - len(bad), "sited", len(bad), "refused")
        for r in bad:
            print(r)
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
