#!/usr/bin/env python3
"""S81.IR ruling (coordinator 2026-10-25 03:08) as a DELTA on a committed plan (no regeneration):

    python3 physical/die_plan/s81/delta_ir_1025.py physical/die_plan/s81/die_plan.json        # S81 stage die
    python3 physical/die_plan/s81/delta_ir_1025.py physical/die_plan/s81_head/die_plan.json   # S81 head die

For every serdes die.io window: macro / domain / core strip from pg_domains.split_domain (PHY macro 2.4 mm2 on the
die-edge side, domain = macro + 63.64-um guard inside the serdes partition, core_strip_um = rest of the partition,
core_edge_bumps relocate), the io window shrunk to the macro (signal sites over the macro), the domain rewritten, and
the u_phy content slot of the serdes type set to the macro (type frame; every instance of the type must agree).
The free area is die_io.phy_zone (63.64-um guard from every ft band / bus boundary-flop strip), so the ft windows,
routes, stations and boundary-flop strips stay in the core strip by construction; a window whose zone is off-shore
(ft strip on the die-edge side, lk_ES0) is left as it is and reported.  Edits die.io, die.pg.domains and the serdes
partition_types' u_phy contents only.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
import die_io as DIO  # noqa: E402
import pg_domains as PG  # noqa: E402


def apply(raw):
    """apply the split to plan dict raw in place; returns the report lines."""
    P = S.Plan(raw)
    W, H = raw["die"]["outline_um"]
    io = raw["die"]["io"]
    doms = {d["io"][0]: d for d in raw["die"]["pg"].get("domains", [])}
    prect = PG.part_rects(raw)
    slots, rep = {}, []
    for w in io:
        if w.get("iface") != "serdes":
            continue
        pn = w["part"]
        t = P.ptype(pn)
        cs = [c for c in t.get("contents", []) if DIO.classify(c.get("module", ""))]
        zone, _ = DIO.phy_zone(P, pn, PG.PHY_GUARD_UM)
        if DIO.edge_dist(P, zone) > DIO.EDGE_MAX_UM + 1e-6:
            rep.append(f"{pn} {P.parts[pn]['type']}: PHY zone {[round(v, 2) for v in zone]} OFF-SHORE "
                       f"({DIO.edge_dist(P, zone):.0f} um): left unsplit (orient / window fix owed)")
            continue
        mac0 = PG.split_domain(zone, prect[pn], W, H)[0]
        ex0 = [e for e in (w.get("bump_exclude_um") or [])]
        if DIO.count_sites(mac0, w["pitch_um"], ex0) < w["signals"]:
            rep.append(f"{pn} {P.parts[pn]['type']}: split macro {mac0} has {DIO.count_sites(mac0, w['pitch_um'], ex0)} "
                       f"sites < {w['signals']} signals: left unsplit (PHY does not fit; window re-lay owed)")
            continue
        w["rect_um"] = [round(v, 4) for v in zone]
        d = doms.get(w["name"])
        if d is None:
            d = PG.domains([w], W, H, prect)[0]
            raw["die"]["pg"].setdefault("domains", []).append(d)
        PG.apply_split(w, d, prect[pn], W, H)
        mac = w["rect_um"]
        a, b = P.to_type(pn, mac[:2]), P.to_type(pn, mac[2:])
        tr = [round(min(a[0], b[0]), 4), round(min(a[1], b[1]), 4), round(max(a[0], b[0]), 4), round(max(a[1], b[1]), 4)]
        for c in cs:
            k = (P.parts[pn]["type"], c["inst"])
            if k in slots and any(abs(u - v) > 0.01 for u, v in zip(slots[k][0], tr)):
                raise SystemExit(f"{pn}: macro {tr} (type frame) != {slots[k][1]}'s {slots[k][0]} (same type)")
            slots[k] = (tr, pn)
        am = (mac[2] - mac[0]) * (mac[3] - mac[1]) / 1e6
        rep.append(f"{pn} {P.parts[pn]['type']} {P.orient(pn)}: macro {mac} {am:.2f} mm2, domain {d['rect_um']}, "
                   f"{len(d['core_strip_um'])} core strip rect(s){'  PHY_SHORT' if am < PG.PHY_AREA_MM2 - 1e-3 else ''}")
    for (tn, ci), (tr, _) in sorted(slots.items()):
        for c in raw["partition_types"][tn]["contents"]:
            if c["inst"] == ci:
                c["origin_um"] = tr[:2]
                c["outline_um"] = [round(tr[2] - tr[0], 4), round(tr[3] - tr[1], 4)]
                c["note"] = (c.get("note", "").split("; S81.IR split")[0] + "; S81.IR split (10-25): PHY macro slot "
                             f"{c['outline_um'][0]:g} x {c['outline_um'][1]:g} um at the die-edge side (= phy_macro_um); "
                             "the rest of the partition is the core strip (boundary flops, ft stations)")
    rep.append(f"delta_ir_1025: {len(slots)} u_phy slots set")
    return rep


def main():
    pf = Path(sys.argv[1])
    raw = json.loads(pf.read_text())
    rep = apply(raw)
    pf.write_text(json.dumps(raw, indent=1) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
