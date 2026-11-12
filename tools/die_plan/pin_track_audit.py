#!/usr/bin/env python3
"""Hard-core pin track audit in the plan frame (S81-T51-PINFIX-1, DRT-0073 class).

A pin on layer L is on-track iff  origin + track_offset + local pin centre == t_off (mod pitch)  [nm, die lattice
schema.ASAP7_LAYERS] on the layer's preferred-direction axis; a mirrored axis (MY / R180 for x, MX / R180 for y) maps
the local centre c to outline - c (as gen_core_kit_legacy.native_m7_phase / m6_pin_grant do).  Reports per layer the
off-track pin count, residues and the shift (nm, in the plan frame) that would put the pins on-track.

  python3 -I pin_track_audit.py PLAN.json [--root REPO_ROOT] [--json OUT] [--layers M7,M5]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema  # noqa: E402

# layer -> (axis, offset_nm, pitch_nm) from the DIE / parent lattice (schema.ASAP7_LAYERS: the tracks the generated
# partition and die kits write; pin layers symmetric, offset = pitch / 2).  S81-T51-PINFIX-2 11-12: this table was the
# ORFS platform make_tracks (M7 16 nm) with M3-M6 axes swapped, so it called the t51 native M7 roots 4 nm off when
# they are 20 nm off the parent M7 tracks (gen_core_kit_legacy.native_m7_phase: core-frame phase 52 nm at [0.108, 0.012]).
TRACKS = {L["name"]: ("x" if L["dir"] == "V" else "y", round(L["offset_um"] * 1000), round(L["pitch_um"] * 1000))
          for L in schema.ASAP7_LAYERS}


def nm(v):
    return int(round(float(v) * 1000))


MIRROR = {"R0": (False, False), "MX": (False, True), "MY": (True, False), "R180": (True, True)}


def audit_pins(pins, origin_um, offset_um, layers, orient="R0", outline_um=None):
    out = {}
    mir = MIRROR[orient]
    if any(mir) and outline_um is None:
        raise ValueError(f"orient {orient} needs the core outline")
    for lay in layers:
        axis, off, pitch = TRACKS[lay]
        ai = 0 if axis == "x" else 1
        res = {}
        n = 0
        for p in pins:
            if p["layer"] != lay:
                continue
            n += 1
            c = nm(outline_um[ai]) - nm(p[axis]) if mir[ai] else nm(p[axis])
            g = nm(origin_um[ai]) + nm(offset_um[ai]) + c
            r = (g - off) % pitch
            if r:
                res[r] = res.get(r, 0) + 1
        shift = None
        if res:
            r = max(res, key=res.get)
            shift = -r if r <= pitch // 2 else pitch - r
        out[lay] = dict(pins=n, offtrack=sum(res.values()), residue_nm=res, shift_nm=shift)
    return out


def audit_plan(plan, repo_root, layers=("M7",)):
    rows, seen = [], set()
    for tname, t in plan["partition_types"].items():
        for hc in t.get("hard_cores") or []:
            key = (hc.get("module"), tuple(hc.get("origin_um") or ()), hc.get("pins_file"))
            if key in seen or not hc.get("pins_file"):
                continue
            seen.add(key)
            pf = Path(repo_root) / "physical/die_plan/s81" / hc["pins_file"]
            if not pf.is_file():
                rows.append(dict(type=tname, module=hc["module"], status="NO_PINS_FILE"))
                continue
            o = hc.get("orient", "R0")
            if o not in MIRROR:
                rows.append(dict(type=tname, module=hc["module"], status="ORIENT_UNKNOWN", orient=o))
                continue
            pins = json.loads(pf.read_text())["pins"]
            a = audit_pins(pins, hc["origin_um"], hc.get("track_offset_um") or [0, 0], layers, o, hc.get("outline_um"))
            rows.append(dict(type=tname, module=hc["module"], orient=o,
                             status="OFFTRACK" if any(v["offtrack"] for v in a.values()) else "OK", layers=a))
    return rows


def main(argv):
    plan = json.loads(Path(argv[1]).read_text())
    root = argv[argv.index("--root") + 1] if "--root" in argv else "."
    layers = tuple(argv[argv.index("--layers") + 1].split(",")) if "--layers" in argv else ("M7",)
    rows = audit_plan(plan, root, layers)
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(rows, indent=1))
    bad = [r for r in rows if r["status"] == "OFFTRACK"]
    for r in bad:
        print(r["type"], r["module"], json.dumps(r["layers"]))
    print(f"pin_track_audit: {len(rows)} cores, {len(bad)} off-track, "
          f"{sum(1 for r in rows if r['status'] in ('NO_PINS_FILE', 'ORIENT_UNKNOWN'))} not evaluated")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
