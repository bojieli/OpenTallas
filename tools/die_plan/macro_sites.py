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

import os as _os_cbc, sys as _sys_cbc
_sys_cbc.path.insert(0, _os_cbc.path.dirname(_os_cbc.path.abspath(__file__)))
import cbc_rules as _CBC  # noqa: E402  OWNER 11-20 #6: generator hop default (300 um), one knob for every die
REACH_UM = _CBC.REACH_UM_PER_HOP
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


HALO_UM = 4.32


def hits(a, b):
    """open-interior overlap of two boxes"""
    return a[0] < b[2] - 1e-8 and b[0] < a[2] - 1e-8 and a[1] < b[3] - 1e-8 and b[1] < a[3] - 1e-8


def covers(a, b):
    """box a overlaps box b, or contains the point box b (zero size): a partner is never under the macro"""
    if b[0] == b[2] and b[1] == b[3]:
        return a[0] - 1e-8 <= b[0] <= a[2] + 1e-8 and a[1] - 1e-8 <= b[1] <= a[3] + 1e-8
    return hits(a, b)


def legal(t, box, obstacles, partner_boxes=()):
    """FABLE-PD-QC-2300: macro box (halo added here) inside the outline margin, clear of every obstacle, covering no
    partner.  Overlap is illegal, never 'gap 0'."""
    W, H = t["outline_um"]; a = [box[0] - HALO_UM, box[1] - HALO_UM, box[2] + HALO_UM, box[3] + HALO_UM]
    if a[0] < GRID_UM - 1e-6 or a[1] < GRID_UM - 1e-6 or a[2] > W - GRID_UM + 1e-6 or a[3] > H - GRID_UM + 1e-6:
        return False
    return not any(hits(a, b) for b in obstacles) and not any(covers(a, p) for p in partner_boxes)


def target(tn, t, inst, size, obstacles=None):
    """origin [x, y] for a size [w, h] macro that minimises max gap(macro box, partner) (coarse 8.64 grid, outline-clamped).
    With obstacles (the generator's occupied list), only legal() boxes count; ValueError when none is legal."""
    W, H = t["outline_um"]; w, h = size; P = partners(tn, t, inst)
    xs = [p[0] for p in P] + [p[2] for p in P]; ys = [p[1] for p in P] + [p[3] for p in P]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    best = None
    for i in range(-30, 31):
        for j in range(-30, 31):
            x = min(max(cx - w / 2 + i * GRID_UM, GRID_UM), W - GRID_UM - w)
            y = min(max(cy - h / 2 + j * GRID_UM, GRID_UM), H - GRID_UM - h)
            if obstacles is not None and not legal(t, [x, y, x + w, y + h], obstacles, P):
                continue
            v = max(gap([x, y, x + w, y + h], p) for p in P)
            k = (round(v, 3), abs(i) + abs(j))
            if best is None or k < best[0]:
                best = (k, [x, y])
    if best is None:
        raise ValueError(f"macro_sites: {tn} {inst}: no legal site within 30 grid steps of its partners")
    return best[1]


def worst_gap(tn, t, inst, origin, size):
    x, y = origin; w, h = size
    return max(gap([x, y, x + w, y + h], p) for p in partners(tn, t, inst))


def _paths(h):
    return {h["inst"], h.get("physical_inst") or h["inst"]}


def inside_hard_core(inst, t, sited=()):
    """QC-PLAN-R3 (COORD 11-20): the hard core (plan inst) whose RTL path holds inst, else None.  The st_a inventory lists
    the 5 SRAMs of each region core u_r<k> (physical_inst u_bound.u_u_r<k>); they are inside that core's LEF, so a
    separate record for them is a KITFIT-OVERLAP with the core.  Cores being re-sited themselves (sited) never count."""
    for h in t.get("hard_cores") or []:
        if h["inst"] in sited:
            continue
        if any(inst.startswith(p + ".") for p in _paths(h)):
            return h["inst"]
    return None


def hard_core_obstacles(t, sited=()):
    """boxes (grown by each core's halo_um) of the type's existing hard cores that are not being re-sited: a new macro
    site may not overlap them (N46T: generator st_a g_btb banks on top of region core u_r0, 110 KITFIT-OVERLAP)"""
    out = []
    for h in t.get("hard_cores") or []:
        if h["inst"] in sited or not (h.get("origin_um") and h.get("outline_um")):
            continue
        b = box_of(h); g = float(h.get("halo_um") or 0.0)
        out.append([b[0] - g, b[1] - g, b[2] + g, b[3] + g])
    return out


def site_points(t):
    """[(kind, [x, y])]: the point sites a macro (box + halo) may not cover: count strap pins, relay_sites (firm stage
    flops), reset consumer / clock tap sites and the reset tap (FABLE-PD-QC-2300 F4: generator st_b SRAMs on the type's
    count straps and tap sites, the class N46R3 had just removed)"""
    out = [("strap", p) for s in t.get("count_straps") or [] for p in s.get("sites_um") or []]
    out += [("relay", p) for p in (t.get("relay_sites") or {}).values() if isinstance(p, (list, tuple)) and len(p) == 2]
    r = t.get("reset") or {}
    out += [("tap", p[1:3]) for p in r.get("consumer_sites_um") or [] if isinstance(p, (list, tuple)) and len(p) >= 3]
    if r.get("tap_um"):
        out.append(("tap", r["tap_um"]))
    return [(k, [float(p[0]), float(p[1])]) for k, p in out]
