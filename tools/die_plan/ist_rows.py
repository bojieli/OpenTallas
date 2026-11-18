"""ist_rows.py -- ordered station rows for a wide rank (S81-COL-ROWS 11-17, FABLE-FIX-S81-COL ir1 proof, COORD).

col_h9_r1 GRT-0116: istations.tcl packs every station of a 1,167-flop frame_int_o0 rank at ONE point (a 147 x 9 um triangle with the
bits in arbitrary order), 898 overflowing gcells in the 61-um north strip.  Form: the rank keeps its planned centre (same y, same rank
centres, no plan or cycle change) and its bits are laid out as ORDERED rows: groups of ten consecutive bits, one group per site column,
columns spread over +-90 um along the face, bit g*10+k at the k-th row of group g.  The result is a plan-style bit_sites_um table that
the existing exact-bank machinery of kit_istations.py (exact_banks / ft_bit_sites.validate_slot) already validates and places.

Opt-in OT_IST_ROWS=1 (kit_wave item_env): default behaviour of every other kit is byte-identical.
"""
import math

GROUP = 10
HALF_SPAN_UM = 90.0
MIN_WIDTH = 256                     # wider ranks only
CELL_UM = (1.08, 0.27)              # DFF footprint (20 CPP x 1 row): lower-left site grid
COLLINEAR_TOL_UM = 1.0


def ordered_rows(width, centre, along="x", *, group=GROUP, half_span_um=HALF_SPAN_UM, cell_um=CELL_UM):
    """[(x, y)] lower-left sites for the width payload bits + the epoch flop (index width), ordered by bit."""
    n = width + 1
    cols = -(-n // group)
    cw, rh = cell_um
    along_pitch = cw if along == "x" else rh
    half = max(half_span_um, (cols - 1) * along_pitch / 2.0)        # never tighter than one cell per column
    pitch = (2.0 * half / (cols - 1)) if cols > 1 else 0.0
    cx, cy = centre
    out = []
    for bit in range(n):
        g, k = divmod(bit, group)
        pos = -half + g * pitch
        if along == "x":                                           # N/S face: columns along x, ten bits stacked in y
            out.append((round(cx + pos, 6), round(cy + (k - (group - 1) / 2.0) * rh, 6)))
        else:                                                      # E/W face: columns along y, ten bits side by side in x
            out.append((round(cx + (k - (group - 1) / 2.0) * cw, 6), round(cy + pos, 6)))
    return out


def rank_axis(regs):
    """'x' when every rank centre has the same y (a row along a N/S face), 'y' when they share x, else None."""
    pts = [tuple(p) for p in regs or []]
    if not pts:
        return None
    if all(abs(p[1] - pts[0][1]) <= COLLINEAR_TOL_UM for p in pts):
        return "x"
    if all(abs(p[0] - pts[0][0]) <= COLLINEAR_TOL_UM for p in pts):
        return "y"
    return None


def apply_ordered_rows(entry, width, env=None):
    """entry + bit_sites_um / bit_site_cell_um (ordered rows at every planned rank centre) when OT_IST_ROWS=1 and the rank qualifies;
    else the entry unchanged (same object).  Never touches an entry that already carries bit_route / bit sites."""
    import os
    if (env if env is not None else os.environ).get("OT_IST_ROWS") != "1":
        return entry
    if width <= MIN_WIDTH or any(k in entry for k in ("bit_route", "bit_sites_um", "face_bit_sites_um", "bit_site_cell_um")):
        return entry
    regs = entry.get("regs_um")
    axis = rank_axis(regs)
    if not regs or axis is None:
        return entry
    out = dict(entry)
    out["bit_sites_um"] = [[list(xy) for xy in ordered_rows(width, tuple(c), axis)] for c in regs]
    out["bit_site_cell_um"] = list(CELL_UM)
    return out
