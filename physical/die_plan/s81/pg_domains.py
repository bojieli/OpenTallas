#!/usr/bin/env python3
"""S81 OWNER DECISION 7 (2026-10-24, IR over SerDes windows): one separate PHY supply per SerDes window.

usage: pg_domains.py PLAN.json DIE_IO.json [--split | --no-split]   (--split is the default, S81.IR ruling 10-25)
Writes die.io (the die_io.py windows) and die.pg.domains into PLAN.json in place, in the same form as HBM B2m
(physical/die_plan/hbm_arch/b2m.py pg_domains) and the S81 head plan: own net VDDPHY with VSS, dense M8/M9 straps over
the window plus a one-bump guard ring, dedicated power/ground C4 rows (45-um array) over the PHY macro.  The partition
strip with boundary flops and ft stations stays on core VDD.  Checked by check.py rule pg_domain.
Basis: TRIAL-S81 10-24 IR: SerDes windows 235/270 mV FAIL on the shared grid.
"""
import copy
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import die_io as DIO  # noqa: E402

PHY_GRID = [dict(layer="M8", width_um=1.92, pitch_um=8.64, offset_um=4.32, nets=["VDDPHY", "VSS"]),
            dict(layer="M9", width_um=1.92, pitch_um=8.64, offset_um=4.32, nets=["VDDPHY", "VSS"])]
PHY_BUMP_PITCH = 45.0
PHY_GUARD_UM = 63.64
# --split (S81.IR ruling, coordinator 2026-10-25 03:08; measured candidate claude/s81-ir-1024r@de34b76ca1,
# results/die_trial_1024/s81_ir_vddphy): the PHY macro at a published 7-nm 112G LR area (0.40 mm2/lane x 6 lanes =
# 2.4 mm2, the HBM B2m IR README figure) on the die-edge side of the window; the VDDPHY domain = macro + guard INSIDE the
# serdes partition (never in a neighbour, adjacent domains never overlap); the rest of the partition is the core strip
# (boundary flops, ft stations, their M8/M9 core grid + core C4).  Ported onto the S81-XDIE form: the free area is the
# die_io.py PHY zone (already `guard` clear of every face-window strip / ft band), the macro is that zone inset by the
# guard on every partition side that faces core (not the die edge), capped to PHY_AREA_MM2 by trimming its inner side
# (8.64-um steps).  A zone too small for PHY_AREA_MM2 keeps the whole inset zone and is flagged phy_short (check
# pg_domain WARN): the type's ft / bus windows must then be re-laid to free the area.
# core_edge_bumps "relocate": a 150-um core lattice C4 that falls inside the domain rect within half a pitch of an edge
# facing core moves 15 um outside that edge (S81.IR E1: core VSS 40.9 mV without it).
PHY_AREA_MM2 = 2.4
GRID = 8.64
EDGE_UM = 200.0


def part_rects(plan):
    pr = {}
    for p in plan["partitions"]:
        w, h = plan["partition_types"][p["type"]]["outline_um"]
        x, y = p["origin_um"]
        pr[p["name"]] = (x, y, x + w, y + h)
    return pr


def _sub(r, d):
    """r minus d as up to four rects (bands below / above d, then left / right of d within its y span)."""
    if not (d[0] < r[2] and d[2] > r[0] and d[1] < r[3] and d[3] > r[1]):
        return [list(r)]
    out = []
    if d[1] > r[1]:
        out.append([r[0], r[1], r[2], d[1]])
    if d[3] < r[3]:
        out.append([r[0], d[3], r[2], r[3]])
    y0, y1 = max(r[1], d[1]), min(r[3], d[3])
    if d[0] > r[0]:
        out.append([r[0], y0, d[0], y1])
    if d[2] < r[2]:
        out.append([d[2], y0, r[2], y1])
    return [[round(v, 4) for v in q] for q in out if q[2] - q[0] > 1e-3 and q[3] - q[1] > 1e-3]


def split_domain(zone, part, W, H, area_mm2=PHY_AREA_MM2, g=PHY_GUARD_UM):
    """(macro, domain, core_strip rects, short) of one serdes window: zone = its die_io PHY zone (or an already placed
    macro footprint: idempotent), part = its partition rect."""
    px0, py0, px1, py1 = part
    edge = dict(W=px0 <= EDGE_UM, S=py0 <= EDGE_UM, E=W - px1 <= EDGE_UM, N=H - py1 <= EDGE_UM)
    # the shoreline the macro sits on: the partition's die-edge side (S / N rows; W / E for a column slot); the guard
    # insets every other side, a die-corner slot's second die-edge side too (one macro slot per serdes type frame)
    side = "S" if edge["S"] else "N" if edge["N"] else "W" if edge["W"] else "E"
    m = [zone[0] if side == "W" else max(zone[0], px0 + g), zone[1] if side == "S" else max(zone[1], py0 + g),
         zone[2] if side == "E" else min(zone[2], px1 - g), zone[3] if side == "N" else min(zone[3], py1 - g)]
    w, h = m[2] - m[0], m[3] - m[1]
    tgt = area_mm2 * 1e6
    if w * h > tgt + 1e-6:
        if side in "SN":
            d = min(h, math.ceil(tgt / w / GRID - 1e-9) * GRID)
            m = [m[0], m[1], m[2], m[1] + d] if side == "S" else [m[0], m[3] - d, m[2], m[3]]
        else:
            d = min(w, math.ceil(tgt / h / GRID - 1e-9) * GRID)
            m = [m[0], m[1], m[0] + d, m[3]] if side == "W" else [m[2] - d, m[1], m[2], m[3]]
    m = [round(v, 4) for v in m]
    dom = [round(max(px0, m[0] - g), 4), round(max(py0, m[1] - g), 4), round(min(px1, m[2] + g), 4),
           round(min(py1, m[3] + g), 4)]
    short = (m[2] - m[0]) * (m[3] - m[1]) < tgt - 1e-3
    return m, dom, _sub(part, dom), short


def domains(io, W, H, prect=None, split=False):
    out = []
    for w in io:
        if w.get("iface") != "serdes":
            continue
        x0, y0, x1, y1 = w["rect_um"]
        g = PHY_GUARD_UM
        ex = w.get("bump_exclude_um") or []
        # S81-XDIE 10-24 (GEOM condition 1): the guard ring stays inside the SerDes partition (no VDDPHY straps over the
        # core-VDD neighbours); the window itself is the PHY zone beside the strip (die_io.py --phy-zone-guard-um)
        bx = prect.get(w["part"], (0.0, 0.0, W, H)) if prect else (0.0, 0.0, W, H)
        out.append(dict(
            name=f"phy_{w['part']}", nets=["VDDPHY", "VSS"], io=[w["name"]],
            rect_um=[round(max(bx[0], x0 - g), 4), round(max(bx[1], y0 - g), 4), round(min(bx[2], x1 + g), 4),
                     round(min(bx[3], y1 + g), 4)],
            grid=copy.deepcopy(PHY_GRID),
            bumps=dict(rect_um=[x0, y0, x1, y1], pitch_um=PHY_BUMP_PITCH, use="power_ground",
                       note="dedicated VDDPHY/VSS C4 rows over the SerDes macro (45-um array); no signal bumps inside "
                            "except the window's own SerDes sites"),
            note="OWNER decision 7 (10-24): separate PHY supply + dedicated bump rows over the SerDes window; core VDD "
                 "grid (partition strip, boundary flops, ft stations) unchanged around it; basis TRIAL-S81 10-24 IR "
                 "235/270 mV FAIL on the shared grid"))
        if ex:
            # S81-XDIE 10-24 (die-corner PHY window, lk_WS2 / lk_EN3 / lk_WN2): no power bumps in the corner stress
            # square either, and that bump-free corner holds the domain's VDDPHY rail-clamp ESD + decap (the job the
            # whole corner keep-out cell did before; the clamp needs no bump over it, only the domain's M8/M9 straps)
            out[-1]["bumps"]["exclude_um"] = [list(e) for e in ex]
            out[-1]["esd_um"] = [list(e) for e in ex]
            out[-1]["note"] += ("; die-corner window: bumps.exclude_um = the corner stress square (no C4 there), "
                                "esd_um = same area: VDDPHY rail clamp + decap")
        if split:
            apply_split(w, out[-1], prect[w["part"]], W, H)
    return out


def apply_split(w, d, part, W, H):
    """--split: shrink io window w to the PHY macro and rewrite its domain d (macro + guard inside the partition)."""
    mac, dom, strip, short = split_domain(w["rect_um"], part, W, H)
    ex = [[round(max(e[0], mac[0]), 4), round(max(e[1], mac[1]), 4), round(min(e[2], mac[2]), 4),
           round(min(e[3], mac[3]), 4)] for e in (w.get("bump_exclude_um") or [])]
    ex = [e for e in ex if e[2] > e[0] + 1e-3 and e[3] > e[1] + 1e-3]
    w["rect_um"] = mac
    if ex:
        w["bump_exclude_um"] = ex
    else:
        w.pop("bump_exclude_um", None)
    w["sites"] = (DIO.count_sites(mac, w["pitch_um"], ex) if ex else
                  max(1, int(math.floor((mac[2] - mac[0]) / w["pitch_um"])) * int(math.floor((mac[3] - mac[1]) / w["pitch_um"]))))
    a = (mac[2] - mac[0]) * (mac[3] - mac[1]) / 1e6
    tag = "S81.IR split (10-25): window = PHY macro %.0f x %.0f um = %.2f mm2" % (mac[2] - mac[0], mac[3] - mac[1], a)
    if short:
        tag += " PHY_SHORT (< %.1f mm2: re-lay the type's ft / bus windows)" % PHY_AREA_MM2
    w["note"] = w["note"].split("; S81.IR split")[0] + "; " + tag
    d.update(rect_um=dom, phy_macro_um=mac, core_strip_um=strip, core_edge_bumps="relocate",
             phy_area_target_mm2=PHY_AREA_MM2)
    d["bumps"]["rect_um"] = list(mac)
    if ex:
        d["bumps"]["exclude_um"] = [list(e) for e in ex]
        d["esd_um"] = [list(e) for e in ex]
    else:
        d["bumps"].pop("exclude_um", None)
        d.pop("esd_um", None)
    d["note"] += ("; S81.IR SPLIT (coordinator 10-25): PHY macro %.2f mm2 on the die-edge side, domain = macro + %.2f-um "
                  "guard inside the partition, core_strip_um on core VDD + core C4 (boundary flops / ft stations), "
                  "core_edge_bumps relocate%s" % (a, PHY_GUARD_UM, "; PHY_SHORT" if short else ""))


def main():
    pf, iof = sys.argv[1], sys.argv[2]
    split = "--no-split" not in sys.argv[3:]
    plan = json.load(open(pf))
    io = json.load(open(iof))
    W, H = plan["die"]["outline_um"]
    plan["die"]["io"] = io
    plan["die"]["pg"]["domains"] = domains(io, W, H, part_rects(plan), split)
    with open(pf, "w") as f:
        json.dump(plan, f, indent=1)
        f.write("\n")
    print(f"pg_domains: {len(plan['die']['pg']['domains'])} VDDPHY domains over {len(io)} die.io windows")


if __name__ == "__main__":
    main()
