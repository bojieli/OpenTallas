"""Connectivity siting of physical-only SRAM/ROM macros (QC-SUST-MACRO-1119, FABLE-CLOSURE 11-19 lever 4).

results/qc_codex_kits_2249/add_macro_sites.py desires() put the QC st macros on a generic quarter-height grid
(st_b u_r{4..7}: row k = r % 4; st_a g_btb[k]: row k), so they landed 450-740 um from the stations / bins they talk to,
far past the 405 um signal reach rule.  This module gives each macro the plan objects it exchanges data with
(partners) and a target that minimises the largest Manhattan gap from the macro box to them; the placer then takes
the nearest legal site to that target.

Partners (plan coordinates, all boxes [x0, y0, x1, y1]):
  st_b  u_u_r<k> region macros: the type's core input leaf = mean leaf_um of internal_stations with capture 'core'
        (every region's pin registers g_pin.r sit there: x_st_a_i / x_hc1_i / x_fw_i chains end at the leaf);
  st_a  g_btb[k] banks: hard cores u_r0 (read address / data port) and cl_b_tw_data_i (write landing / bin);
        u_u_r<k> region macros: hard core u_r<k> when the plan has it, else the core input leaf.
A macro with no partner in the plan raises (a silent grid fallback is what this replaced)."""
import re

REACH_UM = 405.0
GRID_UM = 8.64


def box_of(h):
    x, y = h["origin_um"]; w, hh = h["outline_um"]
    return [x, y, x + w, y + hh]


def gap(a, b):
    """Manhattan gap between two boxes (0 when they touch or overlap)"""
    return max(0.0, a[0] - b[2], b[0] - a[2]) + max(0.0, a[1] - b[3], b[1] - a[3])


def core_leaf(t):
    leafs = [s["leaf_um"] for s in t.get("internal_stations") or [] if s.get("leaf_um") and s.get("capture") == "core"]
    if not leafs:
        return None
    x = sum(p[0] for p in leafs) / len(leafs); y = sum(p[1] for p in leafs) / len(leafs)
    return [x, y, x, y]


def partners(tn, t, inst):
    """the partner boxes of macro inst in type t (see module doc); ValueError when the plan names none"""
    hard = {h["inst"]: box_of(h) for h in t.get("hard_cores") or [] if h.get("origin_um") and h.get("outline_um")}
    out = []
    if re.search(r"g_btb\[\d+\]", inst):
        out = [hard[n] for n in ("u_r0", "cl_b_tw_data_i") if n in hard]
    else:
        m = re.search(r"\.u_u_r(\d)\.", inst)
        if m:
            if "_st_a_" in tn and "u_r" + m[1] in hard:
                out = [hard["u_r" + m[1]]]
            else:
                leaf = core_leaf(t)
                out = [leaf] if leaf else []
    if not out:
        raise ValueError(f"macro_sites: {tn} {inst}: no partner station / bin / core in the plan")
    return out


def target(tn, t, inst, size):
    """origin [x, y] for a size [w, h] macro that minimises max gap(macro box, partner) (coarse 8.64 grid, outline-clamped)"""
    W, H = t["outline_um"]; w, h = size; P = partners(tn, t, inst)
    xs = [p[0] for p in P] + [p[2] for p in P]; ys = [p[1] for p in P] + [p[3] for p in P]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    best = None
    for i in range(-30, 31):
        for j in range(-30, 31):
            x = min(max(cx - w / 2 + i * GRID_UM, GRID_UM), W - GRID_UM - w)
            y = min(max(cy - h / 2 + j * GRID_UM, GRID_UM), H - GRID_UM - h)
            v = max(gap([x, y, x + w, y + h], p) for p in P)
            k = (round(v, 3), abs(i) + abs(j))
            if best is None or k < best[0]:
                best = (k, [x, y])
    return best[1]


def worst_gap(tn, t, inst, origin, size):
    x, y = origin; w, h = size
    return max(gap([x, y, x + w, y + h], p) for p in partners(tn, t, inst))
