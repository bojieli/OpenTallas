"""Top-down pin assignment on partition edges.

Each partition port is placed on the edge of its region that faces the
other end(s) of its net (centroid of the connected regions, or the nearest
die edge for chip IO), at the projection of that target on the edge, then
legalized per edge to a minimum pitch.  Edge overflow spills to the next
edge clockwise.  Horizontal edges get the vertical pin layer and vice versa.
"""
from __future__ import annotations

EDGES = ("left", "bottom", "right", "top")


def _center(r):
    return ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)


def _edge_for(rect, tx, ty):
    cx, cy = _center(rect)
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    dx, dy = tx - cx, ty - cy
    if abs(dx) * h >= abs(dy) * w:
        return "right" if dx >= 0 else "left"
    return "top" if dy >= 0 else "bottom"


def _edge_len(rect, edge):
    return (rect[3] - rect[1]) if edge in ("left", "right") else (rect[2] - rect[0])


def _project(rect, edge, tx, ty):
    """Offset along the edge (from its low end) of the target projection."""
    if edge in ("left", "right"):
        return min(max(ty, rect[1]), rect[3]) - rect[1]
    return min(max(tx, rect[0]), rect[2]) - rect[0]


def _legalize(wanted, length, pitch, margin):
    """wanted: [(offset, key)] -> {key: offset} or None if over capacity."""
    lo, hi = margin, length - margin
    cap = int((hi - lo) / pitch) + 1 if hi >= lo else 0
    if len(wanted) > cap:
        return None
    w = sorted(wanted)
    pos = []
    for off, _ in w:
        p = min(max(off, lo), hi)
        if pos and p < pos[-1] + pitch:
            p = pos[-1] + pitch
        pos.append(p)
    # push back from the high end
    for i in range(len(pos) - 1, -1, -1):
        lim = hi if i == len(pos) - 1 else pos[i + 1] - pitch
        if pos[i] > lim:
            pos[i] = lim
    return {k: round(p, 4) for p, (_, k) in zip(pos, w)}


def assign_pins(regions, port_targets, die, pitch=0.192, margin=1.0,
                h_layer="M4", v_layer="M5", clock_ports=()):
    """regions: {rid: bbox}; port_targets: {(rid, port): [target rid | 'IO']}.

    Returns list of pin dicts (schema PIN_KEYS).
    """
    die_cx, die_cy = _center(die)
    per_edge = {}
    for (rid, port), targets in sorted(port_targets.items()):
        rect = regions[rid]
        if port in clock_ports:
            tx, ty = die_cx, die_cy     # tree root assumed at die centre
        else:
            pts = []
            for t in targets:
                if t == "IO":
                    cx, cy = _center(rect)
                    # nearest die edge point
                    cands = [(cx - die[0], (die[0], cy)), (die[2] - cx, (die[2], cy)),
                             (cy - die[1], (cx, die[1])), (die[3] - cy, (cx, die[3]))]
                    pts.append(min(cands)[1])
                else:
                    pts.append(_center(regions[t]))
            if not pts:
                pts = [(die_cx, die_cy)]
            tx = sum(p[0] for p in pts) / len(pts)
            ty = sum(p[1] for p in pts) / len(pts)
        edge = _edge_for(rect, tx, ty)
        per_edge.setdefault((rid, edge), []).append((_project(rect, edge, tx, ty), port, (tx, ty)))

    placed = []
    pending = sorted(per_edge.items())
    guard = 0
    while pending:
        guard += 1
        if guard > 64:
            raise RuntimeError("pin assignment did not converge (edges over capacity)")
        nxt = {}
        for (rid, edge), lst in pending:
            rect = regions[rid]
            leg = _legalize([(o, p) for o, p, _ in lst], _edge_len(rect, edge), pitch, margin)
            if leg is None:
                # spill the pins whose targets are least aligned with this edge
                lst = sorted(lst, key=lambda t: t[0])
                cap = max(int((_edge_len(rect, edge) - 2 * margin) / pitch) + 1, 0)
                keep, spill = lst[:cap], lst[cap:]
                ne = EDGES[(EDGES.index(edge) + 1) % 4]
                for o, p, tgt in spill:
                    nxt.setdefault((rid, ne), []).append((_project(rect, ne, *tgt), p, tgt))
                lst = keep
                leg = _legalize([(o, p) for o, p, _ in lst], _edge_len(rect, edge), pitch, margin)
            for o, p, _ in lst:
                off = leg[p]
                x0, y0, x1, y1 = rect
                xy = {"left": (x0, y0 + off), "right": (x1, y0 + off),
                      "bottom": (x0 + off, y0), "top": (x0 + off, y1)}[edge]
                placed.append({"region": rid, "port": p, "edge": edge, "offset_um": round(off, 4),
                               "layer": h_layer if edge in ("left", "right") else v_layer,
                               "xy_um": [round(xy[0], 4), round(xy[1], 4)]})
        # merge spills into already-placed edges by re-running those edges
        if nxt:
            done = {(d["region"], d["edge"]) for d in placed}
            again = []
            for key, lst in nxt.items():
                if key in done:
                    old = [d for d in placed if (d["region"], d["edge"]) == key]
                    placed = [d for d in placed if (d["region"], d["edge"]) != key]
                    lst = lst + [(d["offset_um"], d["port"], tuple(d["xy_um"])) for d in old]
                again.append((key, lst))
            pending = again
        else:
            pending = []
    return placed


def io_tcl(pins, rect, pitch):
    """OpenROAD IO constraints for one partition (coordinates local to its die)."""
    lines = ["# generated by opentools/hier pins.py: one slot per pin, place_pins legalizes to tracks"]
    for p in sorted(pins, key=lambda d: (d["edge"], d["offset_um"])):
        lo = max(p["offset_um"] - pitch / 2, 0.0)
        hi = p["offset_um"] + pitch / 2
        lines.append(f"set_io_pin_constraint -pin_names {{{p['port']}}} "
                     f"-region {p['edge']}:{lo:.3f}-{hi:.3f}")
    return "\n".join(lines) + "\n"
