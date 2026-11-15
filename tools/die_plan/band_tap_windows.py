#!/usr/bin/env python3
"""S81-BANDTAP-1115 (COORD 11-15, S81-PHYT1 ASK v2): tap windows in FROZEN ring bands (clock.band_fixed_um).

A ring band point that no planned tap reaches (L1 > tap radius) and that has no legal tap site in reach (the band itself is
the only free area: macro channels) needs a hole in the band where a tap can stand: a HOLE x HOLE square (default 8.64 um =
the 4.32-um tap clear on each side of the tap cell) cut from a band rect.  Greedy set cover over the uncovered points: the
candidate holes sit inside one band rect (so they are macro-free by the band legality itself) at its corners / ends / under
the point; each pick covers the most points within radius, ties go to the fewest new pieces (a hole at a rect end only trims
it) then the least band area.  Rows carry the carved band dicts (clock.band_fixed_um) and clock.band_tap_windows_um (the
holes: the places S81-PHYT1 g2 puts the new taps).  Pieces thinner than 2.16 um are dropped.
usage: band_tap_windows.py PLAN OUT_ROWS REPORT [--types RE] [--hole 8.64] [--radius R]
"""
import argparse, copy, json, re, sys


def pts_of(rect, step=40.0, inset=0.02):
    x0, y0, x1, y1 = rect
    xs = [x0 + inset]
    x = x0 + step
    while x < x1 - inset:
        xs.append(x); x += step
    xs.append(x1 - inset)
    ys = [y0 + inset]
    y = y0 + step
    while y < y1 - inset:
        ys.append(y); y += step
    ys.append(y1 - inset)
    return [(round(a, 3), round(b, 3)) for a in xs for b in sorted(set(ys))]


def carve(rect, hole, min_side=2.16):
    x0, y0, x1, y1 = rect; hx0, hy0, hx1, hy1 = hole
    out = [[x0, y0, x1, hy0], [x0, hy1, x1, y1], [x0, hy0, hx0, hy1], [hx1, hy0, x1, hy1]]
    return [[round(v, 6) for v in r] for r in out if r[2] - r[0] >= min_side - 1e-9 and r[3] - r[1] >= min_side - 1e-9]


def holes_for(rect, p, h):
    x0, y0, x1, y1 = rect
    # a channel rect thinner than the hole is cut through its whole thin side (the channel itself is macro-free and the tap
    # clear applies along the channel): hole = min(h, side) per axis
    hw, hh = min(h, x1 - x0), min(h, y1 - y0)
    xs = {x0, x1 - hw, min(max(x0, p[0] - hw / 2), x1 - hw)}
    ys = {y0, y1 - hh, min(max(y0, p[1] - hh / 2), y1 - hh)}
    return [[round(x, 6), round(y, 6), round(x + hw, 6), round(y + hh, 6)] for x in xs for y in ys]


def plan_type(rects_by_bus, taps, radius, hole=8.64, step=40.0, margin=0.5):
    """rects_by_bus {bus: [rect..]}; taps [(x,y)]; returns (new rects_by_bus, holes, uncovered points)"""
    cur = {b: [list(r) for r in rs] for b, rs in rects_by_bus.items()}
    taps = [tuple(t) for t in taps]
    near = lambda p: any(abs(p[0] - t[0]) + abs(p[1] - t[1]) <= radius for t in taps)
    U = sorted({p for rs in cur.values() for r in rs for p in pts_of(r, step) if not near(p)})
    holes = []; R = radius - margin
    while U:
        best = None
        for b, rs in cur.items():
            for i, r in enumerate(rs):
                half = (r[2] - r[0] + r[3] - r[1]) / 2 + hole
                cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
                near_pts = [p for p in U if abs(p[0] - cx) + abs(p[1] - cy) <= R + half]
                seen = set()
                for p in near_pts:
                    for hl in holes_for(r, p, hole):
                        k = tuple(hl)
                        if k in seen:
                            continue
                        seen.add(k)
                        c = ((hl[0] + hl[2]) / 2, (hl[1] + hl[3]) / 2)
                        cov = sum(1 for q in U if abs(q[0] - c[0]) + abs(q[1] - c[1]) <= R)
                        if not cov:
                            continue
                        pieces = carve(r, hl)
                        lost = (r[2] - r[0]) * (r[3] - r[1]) - sum((q[2] - q[0]) * (q[3] - q[1]) for q in pieces)
                        key = (-cov, len(pieces) - 1, lost, b, i, k)
                        if best is None or key < best[0]:
                            best = (key, b, i, hl, c, pieces)
        if best is None:
            break
        _, b, i, hl, c, pieces = best
        cur[b][i:i + 1] = pieces
        holes.append(dict(bus=b, hole_um=hl, tap_xy=[round(c[0], 3), round(c[1], 3)]))
        taps.append(c)
        U = [q for q in U if abs(q[0] - c[0]) + abs(q[1] - c[1]) > R]
    return cur, holes, U


def _area(rs):
    return sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--types", default=r"."); ap.add_argument("--hole", type=float, default=8.64)
    ap.add_argument("--radius", type=float)
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan)); rows = {}; rep = {}
    for tn, t in sorted(raw["partition_types"].items()):
        ck = t.get("clock") or {}; fx = ck.get("band_fixed_um")
        if not fx or not re.search(a.types, tn):
            continue
        rad = a.radius or float(ck.get("tap_radius_um") or 100.0)
        taps = [x["xy"] for x in list(ck.get("taps") or []) + list(ck.get("added_taps") or []) if x.get("xy")]
        rbb = {b: (v.get("rects_um") or [v["rect_um"]]) for b, v in fx.items() if v.get("rect_um")}
        new, holes, left = plan_type(rbb, taps, rad, a.hole)
        changed = [b for b in new if new[b] != rbb[b]]
        row = copy.deepcopy(fx)
        for b in changed:
            d = row[b]; old = _area(rbb[b]); nw = _area(new[b])
            d["rect_um"] = new[b][0]
            if len(new[b]) > 1:
                d["rects_um"] = new[b]
            else:
                d.pop("rects_um", None)
            if d.get("band_use") is not None and nw > 0:
                d["band_use"] = round(d["band_use"] * old / nw, 4)
            d["tap_windows_um"] = [h["hole_um"] for h in holes if h["bus"] == b]
        if changed:
            rows[tn] = {"clock.band_fixed_um": row, "clock.band_tap_windows_um": [h["hole_um"] for h in holes]}
        rep[tn] = dict(radius=rad, holes=len(holes), changed=changed, uncovered=left,
                       pieces_before=sum(len(v) for v in rbb.values()), pieces_after=sum(len(v) for v in new.values()),
                       area_lost_um2=round(sum(_area(v) for v in rbb.values()) - sum(_area(v) for v in new.values()), 1),
                       holes_list=holes)
    json.dump({"lane": "S81-BANDTAP-1115", "rows": rows}, open(a.out, "w"))
    json.dump(rep, open(a.report, "w"), indent=1)
    print({t: (r["holes"], len(r["uncovered"]), r["pieces_before"], r["pieces_after"]) for t, r in rep.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
