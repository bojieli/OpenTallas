"""ftover.py PLAN TYPE[,TYPE..] [-v] : ft-slot station legs that cross hard-core outlines (bits x um over macros).
Each station = centroid of its bit_sites_um; consecutive stations joined by the better of the two L routes
(the one with less over-macro length). Prints per slot: bits, stations, over-macro um (best L), bits*um."""
import json, sys

plan = json.load(open(sys.argv[1]))
types = sys.argv[2].split(",") if sys.argv[2] != "ALL" else sorted(plan["partition_types"])
verbose = "-v" in sys.argv


def boxes_of(pt):
    out = []
    for c in pt.get("hard_cores", []) or []:
        sz = c.get("size_um") or c.get("outline_um")
        if not sz or not c.get("origin_um"):
            continue
        x, y = c["origin_um"]; w, h = sz
        if str(c.get("orient", "R0")) in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        out.append((c.get("inst"), x, y, x + w, y + h))
    return out


def seg_over(p, q, boxes):
    (x1, y1), (x2, y2) = p, q
    tot = 0.0
    for _, a, b, c, d in boxes:
        if y1 == y2:
            if b < y1 < d:
                lo, hi = sorted((x1, x2)); tot += max(0.0, min(hi, c) - max(lo, a))
        elif x1 == x2:
            if a < x1 < c:
                lo, hi = sorted((y1, y2)); tot += max(0.0, min(hi, d) - max(lo, b))
    return tot


def leg(p, q, boxes):
    r1 = seg_over(p, (q[0], p[1]), boxes) + seg_over((q[0], p[1]), q, boxes)
    r2 = seg_over(p, (p[0], q[1]), boxes) + seg_over((p[0], q[1]), q, boxes)
    return min(r1, r2)


grand = []
for t in types:
    pt = plan["partition_types"].get(t)
    if not pt:
        print("NOTYPE", t); continue
    boxes = boxes_of(pt)
    rows = []
    for fs in pt.get("ft_slots", []) or []:
        sites = fs.get("bit_sites_um") or []
        cents = []
        for st in sites:
            pts = [s for s in st if isinstance(s, (list, tuple)) and len(s) == 2]
            if pts:
                cents.append((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
        over = 0.0; legs = []
        for i in range(len(cents) - 1):
            o = leg(cents[i], cents[i + 1], boxes); over += o; legs.append(round(o, 1))
        w = fs.get("width", 0)
        rows.append((w * over, fs.get("name"), w, len(cents), round(over, 1), legs, cents))
    rows.sort(reverse=True)
    tb = sum(r[0] for r in rows)
    grand.append((tb, t))
    print("TYPE %s cores %d slots %d bit_um_over_macro %.0f" % (t, len(boxes), len(rows), tb))
    for r in rows[: (50 if verbose else 4)]:
        if r[0] > 0 or verbose:
            print("   %-8s bits %5d stations %d over %.1f um  bit*um %.0f legs %s" % (r[1], r[2], r[3], r[4], r[0], r[5]))
            if verbose:
                print("      cents", [(round(a, 1), round(b, 1)) for a, b in r[6]])
print("RANK", [(t, round(v)) for v, t in sorted(grand, reverse=True)[:30]])
