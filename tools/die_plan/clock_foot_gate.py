#!/usr/bin/env python3
"""Static FOOT gate for a die clock plan (COORD 10-26 06:41 ruling: "footless stubs = plan defect, fix the strap/foot
lattice + a static gate before GRT"; METHODOLOGY 12.7b / 12.9d predict-before-build).  Plan-only, seconds, no OpenROAD.

Every die clock tap (core clock entry, glue tap, PHY strip tap) is driven by one stub driver whose input sits on a die
strap (M9 vertical strap x in XS, M8 horizontal strap y in YS).  The stub driver needs a FOOT: a point ON a strap that
is inside a LEGAL driver site, within --max-stub um (Manhattan) of the tap.  Legal driver sites are declared, never
discovered: islands (12.2a/12.2a1 pushdown island rects, every instance) and plan-fixed foot points (e.g. hd_tile-owned
strap points for its glue taps, COORD 06:41); optionally (--soft-legal) any strap point outside every keep-out (hard
core / ROM / PHY rect) -- the non-strict die_clock_mesh mode.  A tap with no foot is FOOTLESS -> FAIL (exit 1) before
any die clock build / GRT.  The gate does not move, trim or pad anything (12.8); it reports.

inputs
  --plan PLAN            die plan (taps via die_clock.plan_taps, keep-outs via die_clock.keepouts)
  --straps J             JSON {"xs": [...], "ys": [...]} or a die_clock_mesh build report / mesh.json carrying
                         meta.lattice.xs/ys (or top-level xs/ys)
  --islands J            JSON list of {"rect_um": [x0,y0,x1,y1], "owner": str} (die frame) or a HEAD island_spec.json
                         ("instances"[].die_hole_um + types hole size)
  --feet J               JSON list of {"xy": [x, y], "owner": str} plan-fixed foot points (optional)
  --taps J               JSON list of [part, port, x, y] replacing plan_taps (optional; e.g. pushdown-moved taps)
  --core-taps-at-island  move every core tap whose part owns exactly-one-matching island instance to that island's
                         centre (12.2a1 pushdown convention: the core clock entry IS its island)
usage: clock_foot_gate.py --plan P --straps S [--islands I] [--feet F] [--max-stub 405] [--out report.json]
"""
import argparse, bisect, json, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load_straps(p):
    d = json.loads(Path(p).read_text())
    for cand in (d, d.get("meta", {}), d.get("meta", {}).get("lattice", {}), d.get("lattice", {})):
        if isinstance(cand, dict) and cand.get("xs") and cand.get("ys"):
            return sorted(float(x) for x in cand["xs"]), sorted(float(y) for y in cand["ys"])
    raise SystemExit(f"clock_foot_gate: no xs/ys strap lattice in {p}")


def load_islands(p):
    d = json.loads(Path(p).read_text())
    if isinstance(d, dict) and "instances" in d:          # HEAD island_spec.json (8.64 holes, die frame LL)
        size = {m: t.get("hole_size_um", 8.64) for m, t in d.get("types", {}).items()}
        out = []
        for i in d["instances"]:
            s = size.get(i.get("module"), 8.64)
            x, y = i["die_hole_um"]
            out.append(dict(rect_um=[x, y, x + s, y + s], owner=i["part"], inst=i.get("inst")))
        return out
    return [dict(r) for r in d]


def seg_point(seg, x, y):
    """nearest point of an axis-aligned segment ((x0,y0),(x1,y1)) to (x, y)."""
    (x0, y0), (x1, y1) = seg
    return min(max(x, x0), x1), min(max(y, y0), y1)


def strap_segments(xs, ys, rects):
    """per strap, the sub-segments lying inside a legal site rect: {('V', i): [(lo, hi, owner)], ('H', j): [...]}."""
    segs = defaultdict(list)
    for r in rects:
        x0, y0, x1, y1 = r["rect_um"]
        for i in range(bisect.bisect_left(xs, x0), bisect.bisect_right(xs, x1)):
            segs[("V", i)].append((y0, y1, r.get("owner", "")))
        for j in range(bisect.bisect_left(ys, y0), bisect.bisect_right(ys, y1)):
            segs[("H", j)].append((x0, x1, r.get("owner", "")))
    for k in segs:
        segs[k].sort()
    return segs


def foot(xs, ys, segs, x, y, max_stub, soft=None):
    """best (stub_um, (fx, fy), strap, owner) over straps within max_stub, or None."""
    best = None
    for axis, coords, c in (("V", xs, x), ("H", ys, y)):
        lo, hi = bisect.bisect_left(coords, c - max_stub), bisect.bisect_right(coords, c + max_stub)
        for i in range(lo, hi):
            s = coords[i]
            d0 = abs(s - c)
            along = y if axis == "V" else x
            for a, b, own in segs.get((axis, i), ()):
                if a - max_stub > along or b + max_stub < along:
                    continue
                q = min(max(along, a), b)
                L = d0 + abs(q - along)
                if L <= max_stub and (best is None or L < best[0]):
                    best = (L, (s, q) if axis == "V" else (q, s), f"{'M9' if axis == 'V' else 'M8'}[{i}]", own)
            if soft is not None:
                q = soft(axis, s, along, max_stub - d0)
                if q is not None:
                    L = d0 + abs(q - along)
                    if best is None or L < best[0]:
                        best = (L, (s, q) if axis == "V" else (q, s), f"{'M9' if axis == 'V' else 'M8'}[{i}]", "soft")
    return best


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--straps", required=True)
    ap.add_argument("--islands")
    ap.add_argument("--feet")
    ap.add_argument("--taps")
    ap.add_argument("--core-taps-at-island", action="store_true")
    ap.add_argument("--soft-legal", action="store_true")
    ap.add_argument("--not-site", action="append", default=[], metavar="TYPE",
                    help="with --soft-legal: partitions of this type are NOT driver sites outside their islands/feet "
                         "(HEAD ISLAND_STRICT: hd_tile glue)")
    ap.add_argument("--max-stub", type=float, default=405.0, help="um Manhattan tap<->foot (12.1e plan reach)")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    import schema as S
    import die_clock as DC
    P = S.Plan(S.load(a.plan))
    xs, ys = load_straps(a.straps)
    isl = load_islands(a.islands) if a.islands else []
    feet = json.loads(Path(a.feet).read_text()) if a.feet else []
    rects = isl + [dict(rect_um=[f["xy"][0], f["xy"][1], f["xy"][0], f["xy"][1]], owner=f.get("owner", "foot"))
                   for f in feet]
    segs = strap_segments(xs, ys, rects)
    if a.taps:
        taps = [tuple(t[:4]) for t in json.loads(Path(a.taps).read_text())]
    else:
        taps = [(p, port, x, y) for p, port, x, y, _ in DC.plan_taps(P)]
    moved = 0
    if a.core_taps_at_island and isl:
        by_part = defaultdict(list)
        for r in isl:
            by_part[r["owner"]].append(r)
        core_ports = {(n, nm) for n, p in P.parts.items() for nm, _, _, _ in S.core_taps(P, p["type"])}
        inst_of = {}
        for n, p in P.parts.items():
            for nm, _, _, tp in S.core_taps(P, p["type"]):
                inst_of[(n, nm)] = (tp.get("name") if isinstance(tp, dict) else str(tp)).rsplit(".clk", 1)[0]
        nt = []
        for part, port, x, y in taps:
            if (part, port) in core_ports:
                r = [q for q in by_part.get(part, []) if q.get("inst") == inst_of.get((part, port))]
                if len(r) == 1:
                    x0, y0, x1, y1 = r[0]["rect_um"]
                    x, y = (x0 + x1) / 2, (y0 + y1) / 2
                    moved += 1
            nt.append((part, port, x, y))
        taps = nt
    soft = None
    if a.soft_legal:
        ko = list(DC.keepouts(P)) + [tuple(P.rect(n))[:4] + (f"{n}/not-site",) for n, p in P.parts.items()
                                     if p["type"] in set(a.not_site)]
        K = DC.KeepIndex(ko, die=(float(P.W), float(P.H)))
        legal = DC.KeepIndex([tuple(r["rect_um"]) + (r.get("owner", ""),) for r in rects])

        def soft(axis, s, along, room, step=4.32):
            if room < 0:
                return None
            k = 0
            while k * step <= room:
                for q in ((along + k * step, along - k * step) if k else (along,)):
                    xy = (s, q) if axis == "V" else (q, s)
                    if K.hit(*xy) is None or legal.hit(*xy, m=0.0) is not None:
                        return q
                k += 1
            return None
    rows, fails = [], []
    for part, port, x, y in taps:
        b = foot(xs, ys, segs, x, y, a.max_stub, soft)
        ptype = P.parts[part]["type"] if part in P.parts else "?"
        row = dict(part=part, type=ptype, port=port, xy=[round(x, 3), round(y, 3)])
        if b is None:
            row["foot"] = None
            fails.append(row)
        else:
            row.update(foot=[round(b[1][0], 3), round(b[1][1], 3)], stub_um=round(b[0], 3), strap=b[2], site=b[3])
        rows.append(row)
    cls = Counter(f"{r['type']}/{r['port'].split('_')[0] if r['port'].startswith('clk') else r['port']}" for r in fails)
    stubs = sorted(r["stub_um"] for r in rows if r.get("foot"))
    rep = dict(gate="clock_foot", verdict="PASS" if not fails else "FAIL", plan=a.plan, straps=a.straps,
               n_xs=len(xs), n_ys=len(ys), islands=len(isl), feet=len(feet), soft_legal=a.soft_legal, not_site=a.not_site,
               max_stub_um=a.max_stub, taps=len(rows), core_taps_moved_to_island=moved, footless=len(fails),
               footless_by_class=dict(cls.most_common()),
               stub_um_p50=stubs[len(stubs) // 2] if stubs else None, stub_um_max=stubs[-1] if stubs else None,
               footless_first=fails[:40])
    if a.out:
        Path(a.out).write_text(json.dumps(dict(rep, rows=rows), indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "footless_first"}))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
