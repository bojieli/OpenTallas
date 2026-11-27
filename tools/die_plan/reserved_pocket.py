"""Find enclosed pockets and straight, capped slits in die-clock site reservations."""

from collections import defaultdict
from itertools import pairwise

SLIT_UM = 2.7
_EPS = 1e-6


def overlaps(a, b):
    return a[0] < b[2] - _EPS and b[0] < a[2] - _EPS and a[1] < b[3] - _EPS and b[1] < a[3] - _EPS


def _bands(rects, width, height):
    """Horizontal strips of constant wall geometry and their exact free intervals."""
    starts, stops = defaultdict(list), defaultdict(list)
    for i, (x0, y0, x1, y1) in enumerate(rects):
        starts[y0].append((i, x0, x1))
        stops[y1].append(i)
    active = {}
    for y0, y1 in pairwise(sorted({0, height, *starts, *stops})):
        for i in stops[y0]:
            del active[i]
        for i, x0, x1 in starts[y0]:
            active[i] = (x0, x1)
        free, high = [], 0
        for x0, x1 in sorted(active.values()):
            if x0 > high + _EPS:
                free.append((high, x0))
            high = max(high, x1)
        if width > high + _EPS:
            free.append((high, width))
        yield y0, y1, free


def _enclosed(bands, width, height):
    parents, boxes = [0], [None]

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    prev = []
    for y0, y1, free in bands:
        this = []
        j = 0
        for x0, x1 in free:
            i = len(parents)
            parents.append(0 if x0 == 0 or x1 == width or y0 == 0 or y1 == height else i)
            boxes.append((x0, y0, x1, y1))
            this.append((x0, x1, i))
            while j < len(prev) and prev[j][1] <= x0 + _EPS:
                j += 1
            k = j
            while k < len(prev) and prev[k][0] < x1 - _EPS:
                a, b = root(i), root(prev[k][2])
                parents[max(a, b)] = min(a, b)
                k += 1
        prev = this
    enclosed = defaultdict(list)
    for i in range(1, len(parents)):
        k = root(i)
        if k:
            enclosed[k].append(boxes[i])
    return list(enclosed.values())


def _slits(bands, width):
    def capped(gap, free):
        return not any(a < gap[1] - _EPS and gap[0] < b - _EPS for a, b in free)

    open_slits, prev, out = {}, [], []
    for i, (y0, y1, free) in enumerate(bands):
        narrow = {g for g in free if 0 < g[0] and g[1] < width and g[1] - g[0] < SLIT_UM - _EPS}
        for gap in open_slits.keys() - narrow:
            lo, left_cap = open_slits.pop(gap)
            if left_cap or capped(gap, free):
                out.append((gap[0], lo, gap[1], y0))
        for gap in narrow - open_slits.keys():
            open_slits[gap] = (y0, i > 0 and capped(gap, prev))
        prev = free
    for (a, b), (lo, left_cap) in open_slits.items():
        if left_cap:
            out.append((a, lo, b, bands[-1][1]))
    return out


def candidates(rects, outline):
    """Return disjoint fill rectangles, grouped by pocket or capped slit."""
    w, h = outline
    rects = sorted({(max(0, a), max(0, b), min(w, c), min(h, d))
                    for a, b, c, d in rects if a < w and b < h and c > 0 and d > 0})
    if len(rects) < 2:
        return []
    bands = list(_bands(rects, w, h))
    groups = _enclosed(bands, w, h)
    def transpose(r):
        return r[1], r[0], r[3], r[2]

    across = list(_bands([transpose(r) for r in rects], h, w))
    for rect in sorted(_slits(bands, w) + [transpose(r) for r in _slits(across, h)]):
        if not any(overlaps(rect, old) for group in groups for old in group):
            groups.append([rect])
    return groups


def wall_rows(t):
    """Only whole placement reservations that also block both M2 and M3 are walls."""
    from gen_phys import route_layer_names

    for row in (t.get("clock") or {}).get("reserved_sites_um", ()):
        if row.get("kind") != "die_clock_tree":
            continue
        layers = set(route_layer_names(row["route_layers"])) if row.get("route_layers") else set()
        if {"M2", "M3"} <= layers:
            yield tuple(row["rect_um"])


def protected_rects(t, tap_rects, reservations):
    from adv_site_in_macro import port_tap_points, sites
    from ft_bit_sites import type_blocks

    out = [*type_blocks(t), *reservations]
    for rects in tap_rects.values():
        out.extend(rects)
    for _, _, x, y, w, h in sites(t):
        out.append((x - 0.054, y - 0.27, x + max(w, 0.054), y + max(h, 0.27)))
    for _, _, x, y in port_tap_points(t):
        out.append((x - 0.054, y - 0.384, x + 0.054, y + 0.384))
    return out


def clear_fill(groups, protected):
    """Preserve a whole candidate whenever it would touch a planned placement or pin."""
    out = []
    for group in groups:
        if not any(overlaps(r, p) for r in group for p in protected):
            out.extend(group)
    return out


def findings(raw, plan_path=None, **_):
    lines = []
    for name, t in sorted(raw.get("partition_types", {}).items()):
        groups = candidates(wall_rows(t), t["outline_um"])
        if groups:
            area = sum((c-a) * (d-b) for group in groups for a, b, c, d in group)
            lines.append(f"{name}: {len(groups)} enclosed or capped reserved-site gaps ({area:.2f} um²)")
    return lines
