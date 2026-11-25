#!/usr/bin/env python3
"""HEAD-WGATE part (2), SPREAD THE GATHER (FABLE-RC-KV 11-25 00:16, row owners KV-OWN-HG-R2 hg / KV-OWN-RSTREACH hgi).

The head gather tree of a head-group type is two 3-stage chains of pure 1-stage registers
(qkh_head_gather_stage):  ectl t0 -> u_hst0_g -> u_head1_u_ftg -> u_hst0_t2 -> head0 eighths
                          ectl t0 -> u_hst1_g -> u_hst1_t1     -> u_hst1_t2 -> head1 eighths
Only the tail (t2) was sited (reg_leaf_split copies, in the W strip / central street); the first two stages were left to
GPL, which pulled them to the W seam, so every 1559-bit ti bus ran to one point (tile x0-200 y600-700).

This tool edits ONLY the existing plan key partition_types[T].reg_leaf_split (no new keys, 0 added cycles):
  * every existing t2 copy is re-sited at its consumer-pin centroid, snapped into the free row channel next to those pins
    (inside the head column, not in a street);
  * the two upstream stages of each chain get a one-copy reg_leaf_split row each (FIRM site): s2 (ftg / t1) in the
    chain's street at the copies' median row, g on the same street between the ectl t pins and s2.
    The street is the free vertical gap next to the head column with the most budget left after the plan's
    internal_stations + ft_slots demand (Fable street_lane_demand counting, cap = width * 48.18 trk/um * 0.6).
Rows are ordered g, s2, t2 so each split sees whole-port connections (split_text is applied in list order).

usage: head_wgate.py PLAN_IN PLAN_OUT TYPES(comma|all-hg|all-hgi) PINS_BASE [--report R.json]
"""
import argparse, collections, json, re, statistics, sys

TV, TH = 48.18, 57.55
CLR = 3.0
CHAINS = (("u_hst0_g", "u_head1_u_ftg", "u_hst0_t2"), ("u_hst1_g", "u_hst1_t1", "u_hst1_t2"),
          ("u_hst2_g", "u_hst2_t1", "u_hst2_t2"), ("u_hst3_g", "u_hst3_t1", "u_hst3_t2"))


def orient(o, x, y, w, h):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


def boxes(t, ign=None):
    return [x for x in [(c["inst"], c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
             c["origin_um"][1] + c["outline_um"][1]) for c in t["hard_cores"]] if not (ign and re.match(ign, x[0]))]


def load_pins(t, base):
    out = {}
    for c in t["hard_cores"]:
        pf = c.get("pins_file")
        if not pf:
            continue
        d = None
        for d0 in (base + "/plan_of_record/", base + "/"):
            try:
                d = json.load(open(d0 + pf)); break
            except Exception:
                pass
        if d is None:
            continue
        ox, oy = c["origin_um"]; w, h = c["outline_um"]
        g = collections.defaultdict(list)
        for q in d["pins"]:
            n = re.sub(r"\[\d+\]$", "", q["name"]); x, y = orient(c["orient"], q["x"], q["y"], w, h)
            g[n].append((ox + x, oy + y))
        out[c["inst"]] = g
    return out


def pin_pts(pins, pat):
    """pat: '<consumer inst>.<port glob>' with u_ prefix on the inst (reg_leaf_split form)"""
    import fnmatch
    inst, port = pat.split(".", 1)
    inst = inst[2:] if inst.startswith("u_") else inst
    pts = []
    for ci, g in pins.items():
        if fnmatch.fnmatch(ci, inst):
            for n, v in g.items():
                if fnmatch.fnmatch(n, port):
                    pts += v
    return pts


def free_gaps(bx, axis_val, along, lo, hi, clr=CLR):
    """free intervals on the line x=axis_val (along='y') or y=axis_val (along='x')"""
    if along == "y":
        blk = sorted((b[2] - clr, b[4] + clr) for b in bx if b[1] - clr < axis_val < b[3] + clr)
    else:
        blk = sorted((b[1] - clr, b[3] + clr) for b in bx if b[2] - clr < axis_val < b[4] + clr)
    free, cur = [], lo
    for a, b in blk:
        if a > cur:
            free.append((cur, a))
        cur = max(cur, b)
    if cur < hi:
        free.append((cur, hi))
    return free


def lanes_of(t, moved=None):
    bw = {b["name"]: b["width"] for b in t["buses"]}
    lanes, seen = [], set()
    for s in t.get("internal_stations", []):
        # duplicate rows (same conn, ends and regs) bind to ONE station chain (bind receipt: planned 5, inserted 5 for 4 rows)
        key = (s.get("conn"), json.dumps(s.get("from_um")), json.dumps(s.get("to_um")), json.dumps(s.get("regs_um")))
        if key in seen:
            continue
        seen.add(key)
        nm = (s.get("launch", "") or "").replace("bus ", "").strip(); w = bw.get(nm)
        if w is None:
            c = (s.get("conn", "") or "").replace("bus:", ""); w = bw.get(c, 1)
        if s.get("bits"):
            w = s["bits"]
        pts = [s.get("from_um")] + s.get("regs_um", []) + [s.get("to_um")]
        name = (s.get("conn") or "") + "|" + (s.get("launch") or "") + "|to=%d" % int((s.get("to_um") or [0])[0])
        if moved and re.search(moved, name):
            continue
        lanes.append((w, [q for q in pts if q]))
    for s in t.get("ft_slots", []):
        if moved and re.search(moved, "ft:" + s["name"]):
            continue
        lanes.append((s["width"], s["regs_um"]))
    return lanes


def street_demand(lanes, x0, x1, yc):
    d = 0
    for w, pts in lanes:
        for a, b in zip(pts, pts[1:]):
            lo, hi = sorted((a[1], b[1]))
            if lo < yc < hi and x0 - 1 <= (a[0] + b[0]) / 2 <= x1 + 1:
                d += w
    return d


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def plan_type(tn, t, pins, log, ign=None, moved=None):
    W, H = t["outline_um"]
    bx = boxes(t, ign)
    lanes = lanes_of(t, moved)
    rls = {r["leaf"]: r for r in t.get("reg_leaf_split", [])}
    # ectl t-pin source (all t* bus pins on ectl cores)
    src_pts = [p for ci, g in pins.items() if ci.startswith("ectl") for n, v in g.items() if n == "t0" for p in v]
    if not src_pts:
        raise ValueError(f"{tn}: no ectl t pins")
    src = (statistics.mean(p[0] for p in src_pts), statistics.mean(p[1] for p in src_pts))
    new_rows, rep = [], dict(type=tn, src=[round(v, 1) for v in src], chains=[])
    for g_leaf, s2_leaf, t2_leaf in CHAINS:
        if t2_leaf not in rls:
            continue
        row = json.loads(json.dumps(rls[t2_leaf]))
        csites, wsum = [], 0
        for c in row["copies"]:
            pts = [p for pat in c["pins"] for p in pin_pts(pins, pat)]
            if not pts:
                raise ValueError(f"{tn} {t2_leaf}.{c['name']}: no consumer pins found")
            cx = statistics.mean(p[0] for p in pts); cy = statistics.mean(p[1] for p in pts)
            ys = sorted(set(round(p[1], 1) for p in pts))
            # channel: free gap on x=cx of height >= 20 um, nearest to the pin rows
            gaps = [g for g in free_gaps(bx, cx, "y", 0, H) if g[1] - g[0] >= 20
                    and min(abs(y - min(max(y, g[0]), g[1])) for y in ys) <= 15]
            if not gaps:
                csites.append((c["name"], c["site_um"], len(pts), c["site_um"] + ["kept:no-channel"]))
                continue
            gy = min(gaps, key=lambda g: min(abs(y - min(max(y, g[0]), g[1])) for y in ys) * len(pts)
                     + sum(abs(p[1] - min(max(p[1], g[0]), g[1])) for p in pts) / len(pts))
            sy = (gy[0] + gy[1]) / 2 if gy[1] - gy[0] <= 120 else min(max(cy, gy[0] + 6), gy[1] - 6)
            old = c["site_um"]
            c["site_um"] = [round(cx, 2), round(sy, 2)]
            csites.append((c["name"], c["site_um"], len(pts), old))
        # street: free vertical gaps on the copies' median row line, nearest the copies, best budget
        ymid = statistics.median(s[1][1] for s in csites)
        xs = [s[1][0] for s in csites]
        cand = []
        heads = [b for b in bx if re.match(r"head\d+_e\d+$", b[0]) and b[4] < src[1]]
        ylo, yhi = ymid, max(b[4] for b in heads)
        streets = [(0.0, W)]
        for y in [ylo + k * (yhi - ylo) / 40 for k in range(41)]:
            fg = free_gaps(bx, y, "x", 0, W)
            streets = [(max(a, c), min(b, d)) for a, b in streets for c, d in fg if min(b, d) - max(a, c) >= 20]
        cys = [c[1][1] for c in csites]
        ys2 = [min(cys) + k * 4.0 for k in range(int((max(cys) - min(cys)) / 4) + 1)]

        def sites_for(g):
            sx = round(max((g[0] + g[1]) / 2, g[0] + 20) if g[0] < 1 else (g[0] + g[1]) / 2, 2)
            # s2 at the row that minimises its worst hop to a copy (copies sit in row channels; the street is free)
            best = min((max(abs(y - cy) + abs(sx - c[1][0]) for cy, c in zip(cys, csites)), y) for y in ys2)
            s2 = [sx, round(best[1], 2)]
            # g on the street: equal hops src -> g -> s2, kept inside the street (<= top of the head rows)
            tot = man(src, s2)
            gy = max(s2[1], min(yhi, src[1] - max(0.0, tot / 2 - abs(src[0] - sx))))
            gs = [sx, round(gy, 2)]
            hops = dict(src_g=round(man(src, gs)), g_s2=round(man(gs, s2)),
                        s2_copy=round(max(man(s2, c[1]) for c in csites)))
            return gs, s2, hops

        for g in streets:
            cap = (g[1] - g[0]) * TV * 0.6
            dem = max(street_demand(lanes, g[0], g[1], y) for y in range(int(ylo), int(yhi), 40))
            dist = min(abs(x - min(max(x, g[0]), g[1])) for x in xs)
            gs, s2, hops = sites_for(g)
            cand.append(((dem + 1559) / cap, dist, g, dem, cap, gs, s2, hops))
        if not cand:
            raise ValueError(f"{tn} {t2_leaf}: no street")
        near = [c for c in cand if c[1] <= 150]
        if not near:
            raise ValueError(f"{tn} {t2_leaf}: no street within 150 um of the head column (streets {[c[2] for c in cand]})")
        # budget first (gather alone <= 0.6 of raw tracks = 1.0 of cap60), then the shortest worst hop
        pick = min(near, key=lambda c: (c[0] > 1.02, max(c[7].values()), c[0]))
        g, gs, s2, hops = pick[2], pick[5], pick[6], pick[7]
        alts = [dict(street=[round(c[2][0]), round(c[2][1])], ratio=round(c[0], 2), max_hop=max(c[7].values())) for c in near]
        for leaf, site, pins_pat in ((g_leaf, gs, [s2_leaf + ".*"]), (s2_leaf, s2, [t2_leaf + ".*"])):
            new_rows.append({"leaf": leaf, "copies": [{"name": "a", "pins": pins_pat, "site_um": site}]})
        new_rows.append(row)
        rep["chains"].append(dict(leaf=t2_leaf, street=[round(g[0], 1), round(g[1], 1)], street_bits=pick[3],
                                  street_cap60=round(pick[4]), ratio_with_gather=round(pick[0], 2), g_site=gs, s2_site=s2,
                                  copies=[dict(name=n, site=s, old=o, pins=k) for n, s, k, o in csites], hops=hops, alternatives=alts))
        log(f"{tn} {t2_leaf}: street {g[0]:.0f}-{g[1]:.0f} ({pick[3]}+1559)/{pick[4]:.0f}={pick[0]:.2f} g@{gs} s2@{s2} "
            + " ".join(f"{n}@{s}<-{o}" for n, s, k, o in csites) + f" hops {hops} alts {alts}")
    keep = [r for r in t.get("reg_leaf_split", []) if r["leaf"] not in {x["leaf"] for x in new_rows}]
    t["reg_leaf_split"] = keep + new_rows
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in"); ap.add_argument("plan_out"); ap.add_argument("types"); ap.add_argument("pins_base")
    ap.add_argument("--report")
    ap.add_argument("--moved-lanes", default=None, help="regex of station/ft lanes another row moves out (excluded from street demand)")
    ap.add_argument("--ignore-cores", default=None, help="regex of hard cores treated as moved (e.g. ^cl_ft\\d+_i$ under part 1)")
    a = ap.parse_args()
    p = json.load(open(a.plan_in))
    pt = p["partition_types"]
    if a.types == "all-hg":
        tns = [k for k in pt if re.match(r"kv3_hg(_v|$)", k)]
    elif a.types == "all-hgi":
        tns = [k for k in pt if re.match(r"kv3_hgi(_v|$)", k)]
    else:
        tns = a.types.split(",")
    reps = []
    for tn in tns:
        reps.append(plan_type(tn, pt[tn], load_pins(pt[tn], a.pins_base), print, a.ignore_cores, a.moved_lanes))
    json.dump(p, open(a.plan_out, "w"), indent=1)
    if a.report:
        json.dump(reps, open(a.report, "w"), indent=1)


if __name__ == "__main__":
    main()
