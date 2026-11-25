#!/usr/bin/env python3
"""adv_ft_outside.py -- ADV-FT-OUTSIDE (FP-CONVERGE-S81 11-25, report only).

A feed-through slot's station registers (ft_slots[].regs_um) and its exact bit sites (ft_slots[].bit_sites_um, each + bit_site_cell_um)
must lie inside the type outline.  S81 leaf t10 ft7: the last (N out-face) register at y 1252.7 and 1,105 bit sites up to y 1259.8 on a
1226.88-um outline; adv_bank_offarea only reads internal_stations, so the placer found the sites off the die.  One line per type.
"""

TOL = 0.01


def _w(*p):
    return "WARN ADV-FT-OUTSIDE " + " ".join(str(x) for x in p)


def type_hits(t):
    """[(slot name, n sites outside, n regs outside, worst overshoot um)]"""
    o = t.get("outline_um")
    if not o:
        return []
    W, H = o
    hits = []
    for s in t.get("ft_slots") or []:
        if not isinstance(s, dict):
            continue
        cw, ch = (s.get("bit_site_cell_um") or [0.0, 0.0])[:2]
        ns = nr = 0
        worst = 0.0
        for st in s.get("bit_sites_um") or []:
            for x, y in st:
                over = max(-x, -y, x + cw - W, y + ch - H)
                if over > TOL:
                    ns += 1
                    worst = max(worst, over)
        for x, y in s.get("regs_um") or []:
            over = max(-x, -y, x - W, y - H)
            if over > TOL:
                nr += 1
                worst = max(worst, over)
        if ns or nr:
            hits.append((s.get("name"), ns, nr, round(worst, 2)))
    return hits


def findings(raw, plan_path, tree=None, **kw):
    out = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        h = type_hits(t)
        if h:
            out.append(_w(f"{tn}: ft slot(s) outside the {t['outline_um']} outline: " +
                          "; ".join(f"{n} {a} site(s), {b} reg(s), worst +{w} um" for n, a, b, w in h[:6]) +
                          " (fix: shift the station rows inside, 0 cycles)"))
    return out
