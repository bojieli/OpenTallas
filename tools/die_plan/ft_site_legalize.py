#!/usr/bin/env python3
"""QC-SUC-FTSITE 11-24: census + legalize explicit FT bit sites (ft_slots[*].bit_sites_um) so no two bit footprints
(bit_site_cell_um) overlap on the kit core grid.

Cause it fixes: a plan row that maps y through a compressing band (ALLFIX-QC SU2R su2r.py fy(): y 880..1100 squeezed
into 1031.2..1100, factor 0.313) also moved the per-bit FT sites, so the su_c cws1/cws2 stage-0 columns (13 bits at
the 0.27 um row pitch) came out 0.084 um apart: hundreds of overlapping cells, and gen_phys stops in
ft_bit_sites.snap_slots ("FT bit sites ... snap to one site").  Per-bit station rows (x_su_l1_ctl) also step 0.054 um
in x inside one row.  This tool is the generic repair: ft_bit_sites.legalize_slots keeps every free site and moves each
conflicting bit to the nearest free grid site (core box, off hard cores + 1.08 um, off internal-station sites).
Positions only, 0 cycles; stations, stage count, windows, pins and RTL are unchanged.

    ft_site_legalize.py PLAN --census                        list types with snap collisions / footprint overlaps
    ft_site_legalize.py PLAN OUT LEDGER [--types T ...]      rewrite those types (default: every type with a conflict)
"""
import argparse, collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ft_bit_sites as FB  # noqa: E402
from kit_fit import kit_core_area  # noqa: E402

HALO = 1.08


def fixed_sites(t):
    out = []
    for st in t.get("internal_stations", []) or []:
        w, h = st.get("bit_site_cell_um") or (1.404, 0.27)
        for i, stage in enumerate(st.get("bit_sites_um") or []):
            for b, (x, y) in enumerate(stage):
                out.append((f"ist:{st.get('conn')},{i},{b}", x, y, w, h))
    return out


def snap_dups(slots, origin):
    try:
        FB.snap_slots(slots, origin)
        return None
    except ValueError as ex:
        return str(ex)


def census(P, types=None):
    rows = []
    for tn, t in sorted(P["partition_types"].items()):
        if types and tn not in types:
            continue
        slots = [s for s in t.get("ft_slots", []) or [] if s.get("bit_sites_um")]
        if not slots:
            continue
        org = kit_core_area(t)[:2]
        pairs = FB.footprint_conflicts(slots, org, fixed=fixed_sites(t))
        snap = snap_dups(slots, org)
        if pairs or snap:
            by = collections.Counter(a.rsplit(",", 1)[0] if a.rsplit(",", 1)[0] == b.rsplit(",", 1)[0]
                                     else f"{a.rsplit(',', 1)[0]}|{b.rsplit(',', 1)[0]}" for a, b in pairs)
            rows.append(dict(type=tn, overlaps=len(pairs), gen_snap_error=snap, by_stage=dict(by.most_common())))
    return rows


def legalize_type(t):
    a = kit_core_area(t)
    blocks = []
    try:
        from placement_obstacles import placement_boxes
        blocks = list(placement_boxes(t, halo=HALO).values())
    except Exception as ex:      # plain type without placed-macro metadata: hard_cores boxes only
        print(f"placement_boxes unavailable ({type(ex).__name__}: {ex}); using hard_cores", file=sys.stderr)
        for h in t.get("hard_cores", []) or []:
            if h.get("origin_um") and h.get("outline_um"):
                (x, y), (w, hh) = h["origin_um"], h["outline_um"]
                blocks.append((x - HALO, y - HALO, x + w + HALO, y + hh + HALO))
    slots = t.get("ft_slots", []) or []
    new, moves = FB.legalize_slots(slots, a[:2], a, blocks=blocks, fixed=fixed_sites(t))
    return new, moves


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("out", nargs="?"); ap.add_argument("ledger", nargs="?")
    ap.add_argument("--census", action="store_true"); ap.add_argument("--types", nargs="*")
    a = ap.parse_args()
    P = json.load(open(a.plan))
    rows = census(P, a.types)
    if a.census or not a.out:
        print(json.dumps(rows, indent=1))
        return 1 if rows else 0
    types = a.types or [r["type"] for r in rows]
    led = dict(tool="ft_site_legalize.py", plan=a.plan, types={})
    for tn in types:
        t = P["partition_types"][tn]
        new, moves = legalize_type(t)
        t["ft_slots"] = new
        t["note"] = (t.get("note", "") + f" | QC-SUC-FTSITE 11-24 ft_site_legalize: {len(moves)} overlapping FT bit sites"
                     f" moved to the nearest free grid site (max {max([m[3] for m in moves] or [0])} um), positions only")
        per = collections.Counter(m[0].rsplit(",", 1)[0] for m in moves)
        led["types"][tn] = dict(moved=len(moves), max_move_um=max([m[3] for m in moves] or [0]),
                                by_stage=dict(per.most_common()), moves=moves)
        print(tn, "moved", len(moves), "max", led["types"][tn]["max_move_um"], "um")
    left = census(P, types)
    led["after"] = left
    json.dump(P, open(a.out, "w"), separators=(",", ":"))
    json.dump(led, open(a.ledger, "w"), indent=1)
    if left:
        print("STILL CONFLICTING", json.dumps(left)[:2000]); return 2
    print("CLEAN", len(types), "types")
    return 0


if __name__ == "__main__":
    sys.exit(main())
