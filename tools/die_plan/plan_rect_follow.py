"""Rect and window followers for the EDGESTRIP / SVC-YTRADE Y-moves (FAM-S81-SVC-OWN 11-24).

A Y trade or edge-strip move shifts the N-anchored (or S-anchored) geometry of a type by G.  The older walk only moved
2-number points, so the 4-number rects (clock band_fixed_um / landing_contract rect_um, rects_um) and the [[x0, x1], [y0, y1]]
tap windows stayed at their old y: after a 34.56 um N shrink of svc_lo_dsdv_svc_rs__t7 the attn_i0 band sat 8.64 um above the new
outline and the kit died in landing_place.band_rects ("rects_um entry ... outside the type outline").  This module moves a rect or
a tap window as ONE shape (both y ends, same delta) and reports a shape that straddles the anchor instead of stretching it.
"""
RECT_KEYS = frozenset({"rect_um", "rects_um", "tap_windows_um", "band_tap_windows_um", "tap_reserved_um"})   # a rect, or a list of rects
WIN2_KEYS = frozenset()   # (the [[x0, x1], [y0, y1]] form is handled below when a RECT key holds it)
SKIP = frozenset({"buses", "dead_inputs", "relay_depth", "verilog_defines", "count_straps"})


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_rect(v):
    return isinstance(v, list) and len(v) == 4 and all(_num(z) for z in v)


def is_win2(v):
    return (isinstance(v, list) and len(v) == 2 and all(isinstance(w, list) and len(w) == 2 and all(_num(z) for z in w) for w in v))


def follow_rect(r, dy, rnd=lambda v: round(v, 4)):
    """dy(y) -> delta for ONE y coordinate (the same rule the point walk uses).  A rect whose two edges follow different
    anchors changes height (an N band keeps its top on the N face while its bottom stays on the cores); a result with
    no height is refused.  -> (new rect, status)."""
    y0, y1 = rnd(r[1] + dy(r[1])), rnd(r[3] + dy(r[3]))
    if y0 == r[1] and y1 == r[3]:
        return r, "keep"
    if y1 - y0 <= 1e-6:
        return r, "straddle"
    return [r[0], y0, r[2], y1], "moved"


def follow_win2(w, dy, rnd=lambda v: round(v, 4)):
    y0, y1 = rnd(w[1][0] + dy(w[1][0])), rnd(w[1][1] + dy(w[1][1]))
    if y0 == w[1][0] and y1 == w[1][1]:
        return w, "keep"
    if y1 - y0 <= 1e-6:
        return w, "straddle"
    return [list(w[0]), [y0, y1]], "moved"


def walk_shapes(o, moves, on_problem, path=""):
    """Follow every rect / 2x2 tap window below `o` in place.  -> number of shapes moved."""
    n = 0
    if isinstance(o, dict):
        for k, v in list(o.items()):
            if k in SKIP:
                continue
            if k in RECT_KEYS and is_win2(v):
                new, st = follow_win2(v, moves)
                n += st == "moved"
                if st == "straddle":
                    on_problem(f"{path}/{k} {v} collapses")
                o[k] = new
            elif k in RECT_KEYS and is_rect(v):
                new, st = follow_rect(v, moves)
                n += st == "moved"
                if st == "straddle":
                    on_problem(f"{path}/{k} {v} straddles the moved edge")
                o[k] = new
            elif k in RECT_KEYS and isinstance(v, list):
                for i, r in enumerate(v):
                    if is_win2(r):
                        new, st = follow_win2(r, moves)
                        n += st == "moved"
                        v[i] = new
                    elif is_rect(r):
                        new, st = follow_rect(r, moves)
                        n += st == "moved"
                        if st == "straddle":
                            on_problem(f"{path}/{k}/{i} {r} straddles the moved edge")
                        v[i] = new
            elif k in WIN2_KEYS and is_win2(v):
                new, st = follow_win2(v, moves)
                n += st == "moved"
                if st == "straddle":
                    on_problem(f"{path}/{k} {v} straddles the moved edge")
                o[k] = new
            elif k in WIN2_KEYS and isinstance(v, list):
                for i, w in enumerate(v):
                    if is_win2(w):
                        new, st = follow_win2(w, moves)
                        n += st == "moved"
                        if st == "straddle":
                            on_problem(f"{path}/{k}/{i} {w} straddles the moved edge")
                        v[i] = new
            elif isinstance(v, (dict, list)):
                n += walk_shapes(v, moves, on_problem, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, (dict, list)):
                n += walk_shapes(v, moves, on_problem, f"{path}/{i}")
    return n


def n_edge_moves(H, top, g, edge):
    """N shrink by g: a y at or above top + g (the N strip, or on the N edge) moves -g; a y below stays (same as the point rule)."""
    return lambda y: -g if (y >= top + g - 1e-6 or y >= H - edge) else 0.0


def s_grow_moves(g, edge):
    """S grow by g (the interior shifts +g): a y on the S edge (<= edge) stays; every other y moves +g."""
    return lambda y: 0.0 if y <= edge else g
