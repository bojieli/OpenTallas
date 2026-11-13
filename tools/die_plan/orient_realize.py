#!/usr/bin/env python3
"""LEAF-DRT73-1 11-13: plan hard cores in an orient whose pins cannot sit on the kit tracks -> the nearest realizable one.

Class (S81 kit wave 7073a6b4a59, 8 leaf types t13 t21 t29 t30 t39 t44 t51 t65, 11-08 t36 t46 t65 'fault'):
[ERROR DRT-0073] No access point for u_bound.u_u_..._u_vp_g_ln_K_u_l/c0[0] (ot_dsrom_su_hcpost_lane_pr) at GRT pin access,
after place + CTS (~4 h).  The signed hcpost lane LEF has 81 M3 (pitch 0.036, phase 0.009) and 83 M5 (pitch 0.048) pins
on its N/S faces.  In R0/MX the kit origin x = 0.108 mod 0.144 puts both layers on track; in an x-mirror (MY, R180) M3
needs origin = 18 nm mod 36 and M5 a multiple of 12 nm: no origin exists (macro_grid_snap 'unrealizable').  The plan
(ready12bA, plan_r12bA6 = kit-wave plan_h2_2249) has 36 R180 + 18 MY hcpost lanes in 30 leaf types.

Rule: an unrealizable orient drops the mirror of each failing axis (x: R180 -> MX, MY -> R0; y: R180 -> MY, MX -> R0),
so the face that carries the most pins of the failing axis keeps its side; the box (origin, outline) is unchanged.
track_offset_um keeps its value per axis when still on track, else the smallest on-track shift >= 0 is taken.
Faces whose side changes are listed per core (pins per face) in the report: the plan owner re-derives what was computed
from those pin positions (core taps / clock entry points, internal_stations lane ends) in the same plan event.

  python3 tools/die_plan/orient_realize.py PLAN_IN [--out PLAN_OUT] [--report REPORT.json] [--root REPO] [--types RE]
Without --out nothing is written but the report (a dry run); exit 0 always unless a core has no realizable orient (2).
"""
import argparse
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import macro_grid_snap as MGS  # noqa: E402

FACE_SWAP = {"MX": ("N", "S"), "MY": ("E", "W")}


def plan_tracks(plan):
    """the kit track table gen_phys writes for this plan (make_tracks_tcl), as macro_grid_snap reads it"""
    import gen_phys
    import schema
    layers = {L["name"]: L for L in plan.get("layers", schema.ASAP7_LAYERS)}
    return MGS.tracks_for(gen_phys.make_tracks_tcl(SimpleNamespace(layers=layers)))


def _mirrors(o):
    return {"MX": o in ("MX", "R180"), "MY": o in ("MY", "R180")}


def faces(spec):
    """pins per face of the macro frame (nearest outline edge of the pin rect centre)"""
    w, h, pins = spec
    out = {}
    for _n, _l, x0, y0, x1, y1 in pins:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        f = min([(cx, "W"), (w - cx, "E"), (cy, "S"), (h - cy, "N")])[1]
        out[f] = out.get(f, 0) + 1
    return out


def offset_for(spec, o, tracks, origin, cur):
    """per axis: cur when origin + cur puts that axis on track at o, else the smallest shift >= 0 (um, 1 nm)"""
    res = []
    for i, a in enumerate(("x", "y")):
        ph, period = MGS.axis_phases(spec, o, tracks, a)
        o_nm = int(round((origin[i] + cur[i]) * 1000))
        if not ph or o_nm % period in ph:
            res.append(cur[i])
            continue
        base = int(round(origin[i] * 1000))
        res.append(min((p - base) % period for p in ph) / 1000.0)
    return res


def realize(plan, root, types_re=None, tracks=None):
    """-> (changes, refused).  Mutates plan in place."""
    tracks = tracks or plan_tracks(plan)
    specs, real, changes, refused = {}, {}, [], []
    rx = re.compile(types_re) if types_re else None
    for tn, t in sorted(plan["partition_types"].items()):
        if rx and not rx.search(tn):
            continue
        for hc in t.get("hard_cores") or []:
            lef = hc.get("lef")
            if not lef:
                continue
            key = (lef, hc.get("physical_master") or hc["module"])
            if key not in specs:
                p = Path(root) / lef
                specs[key] = MGS.lef_master(p, key[1]) if p.is_file() else None
            spec = specs[key]
            if not spec or not spec[2]:
                continue
            o = hc.get("orient", "R0")
            if (key, o) not in real:
                real[(key, o)] = all(MGS.orient_realizable(spec, o, tracks).values())
            if real[(key, o)]:
                continue
            n = MGS.nearest_realizable_orient(spec, o, tracks)
            if n is None:
                refused.append(dict(type=tn, inst=hc["inst"], module=key[1], orient=o,
                                    realizable=MGS.realizable_orients(spec, tracks)))
                continue
            cur = list(hc.get("track_offset_um") or [0.0, 0.0])
            new_off = offset_for(spec, n, tracks, hc["origin_um"], cur)
            fc = faces(spec)
            swapped = {m: {f: fc.get(f, 0) for f in FACE_SWAP[m]}
                       for m in ("MX", "MY") if _mirrors(o)[m] != _mirrors(n)[m]}
            changes.append(dict(type=tn, inst=hc["inst"], module=key[1], orient=[o, n],
                                track_offset_um=[cur, new_off], origin_um=list(hc["origin_um"]),
                                faces_change_side=swapped,
                                unrealizable_axes=[a for a, v in MGS.orient_realizable(spec, o, tracks).items() if not v]))
            hc["orient"] = n
            hc["track_offset_um"] = new_off
    return changes, refused


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--report")
    ap.add_argument("--root", default=".")
    ap.add_argument("--types")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    changes, refused = realize(plan, a.root, a.types)
    rep = dict(schema="opentallas.orient_realize.v1", by="LEAF-DRT73-1", plan=a.plan, changed=len(changes),
               types=len({c["type"] for c in changes}), refused=refused,
               by_move={f"{o}->{n}": sum(1 for c in changes if c["orient"] == [o, n])
                        for o, n in sorted({tuple(c["orient"]) for c in changes})},
               changes=changes)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    if a.out and changes:
        Path(a.out).write_text(json.dumps(plan, indent=1) + "\n")
    print(f"ORIENT_REALIZE {len(changes)} core(s) in {rep['types']} type(s) {rep['by_move']}; refused {len(refused)}"
          + (f"; wrote {a.out}" if a.out and changes else ""))
    return 2 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
