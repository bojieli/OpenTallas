#!/usr/bin/env python3
"""S81-LEAF-PLAN 11-15 (COORD, GENBUG G1 follow-up): internal_stations rows (lane pads / core relays) with a hop over
the reach between from_um, regs_um[*] and to_um (Manhattan) are re-spaced at equal arc length along the row's own
polyline (from -> regs -> to), so every hop <= L/(n+1); stations are added (n+1) only when L/(n+1) > LIMIT, which is a
+1 register on that conn (reported; the caller prices it with LATCHECK).  Sites stay off placed macros
(ft_seam_fix.off_macro); bus rows of one bus keep one station count (the kit merges them), so a bus is grown as a whole.

    istation_respace.py PLAN OUT LEDGER [--limit 400] [--report 405] [--types RE]
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import ft_seam_fix as SF  # noqa: E402


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def hops(e):
    pts = [e["from_um"]] + list(e["regs_um"]) + [e["to_um"]]
    return [md(a, b) for a, b in zip(pts, pts[1:])]


def at_arc(pts, s):
    """point at Manhattan arc length s along the polyline pts (each leg x first, then y)."""
    legs = []
    for a, b in zip(pts, pts[1:]):
        c = (b[0], a[1])
        legs += [(a, c), (c, b)]
    for a, b in legs:
        d = md(a, b)
        if s <= d + 1e-9:
            f = s / d if d else 0.0
            return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]
        s -= d
    return list(pts[-1])


def respace(t, e, n, boxes):
    pts = [e["from_um"]] + list(e["regs_um"]) + [e["to_um"]]
    L = sum(md(a, b) for a, b in zip(pts, pts[1:]))
    out = []
    for j in range(1, n + 1):
        p = SF.off_macro(boxes, np.array(at_arc(pts, L * j / (n + 1)), float))
        if p is None:
            return None
        out.append([round(float(p[0]), 3), round(float(p[1]), 3)])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("ledger")
    ap.add_argument("--limit", type=float, default=400.0); ap.add_argument("--report", type=float, default=405.0)
    ap.add_argument("--types")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    led = dict(rows=[], refused=[])
    for tn, t in raw["partition_types"].items():
        if a.types and not re.search(a.types, tn):
            continue
        rows = [(i, e) for i, e in enumerate(t.get("internal_stations", [])) if e.get("regs_um") and e.get("from_um")
                and e.get("to_um")]
        bad = [(i, e) for i, e in rows if max(hops(e)) > a.report]
        if not bad:
            continue
        boxes = SF.macro_boxes(t)
        groups = defaultdict(list)            # bus rows of one bus share a count
        for i, e in bad:
            groups[e["conn"] if str(e.get("conn", "")).startswith("bus:") else ("row", i)].append((i, e))
        for g, es in groups.items():
            if isinstance(g, str):
                es = [(i, e) for i, e in rows if e.get("conn") == g]
            n0 = len(es[0][1]["regs_um"])
            new = None
            for n in range(n0, n0 + 5):
                if max(sum(hops(e)) / (n + 1) for _, e in es) > a.limit:
                    continue
                cand = [respace(t, e, n, boxes) for _, e in es]
                if all(r is not None and max(hops(dict(e, regs_um=r))) <= a.limit for (_, e), r in zip(es, cand)):
                    new = cand
                    break
            if new is None:
                led["refused"].append(dict(type=tn, rows=[i for i, _ in es], why="no off-macro spacing <= limit within +4"))
                continue
            for (i, e), r in zip(es, new):
                h0 = round(max(hops(e)), 1)
                e["regs_um"] = r
                e["note"] = (e.get("note", "") + " | istation_respace 11-15: equal-arc re-space, %d->%d stages, max hop "
                             "%.1f->%.1f um" % (n0, n, h0, max(hops(e)))).strip(" |")
                led["rows"].append(dict(type=tn, row=i, conn=e.get("conn"), stages=[n0, n], hop=[h0, round(max(hops(e)), 1)]))
    Path(a.out).write_text(json.dumps(raw) + "\n")
    Path(a.ledger).write_text(json.dumps(led, indent=1) + "\n")
    add = [r for r in led["rows"] if r["stages"][1] > r["stages"][0]]
    print("ISTATION_RESPACE rows %d (stage adds %d), refused %d, worst after %.1f" % (
        len(led["rows"]), len(add), len(led["refused"]), max([r["hop"][1] for r in led["rows"]] or [0])))
    return 0 if not led["refused"] else 1


if __name__ == "__main__":
    sys.exit(main())
