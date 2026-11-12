#!/usr/bin/env python3
"""Hard-core pin track audit in the plan frame (S81-T51-PINFIX-1, DRT-0073 class).

A pin on layer L is on-track iff  origin + track_offset + local pin centre == t_off (mod pitch)  [nm, ASAP7 tracks]
on the layer's preferred-direction axis.  Reports per layer the off-track pin count, residues and the shift (nm)
that would put the pins on-track.  Non-R0 orientations are listed but not evaluated.

  python3 -I pin_track_audit.py PLAN.json [--root REPO_ROOT] [--json OUT] [--layers M7,M5]
"""
import json
import sys
from pathlib import Path

# layer -> (axis, offset_nm, pitch_nm); M7 per tools/check_macro_track_alignment.ASAP7_TRACKS_NM
TRACKS = {"M3": ("y", 12, 48), "M4": ("x", 12, 48), "M5": ("y", 12, 48), "M6": ("x", 0, 48),
          "M7": ("x", 16, 64), "M8": ("y", 20, 80), "M9": ("x", 20, 80)}


def nm(v):
    return int(round(float(v) * 1000))


def audit_pins(pins, origin_um, offset_um, layers):
    out = {}
    for lay in layers:
        axis, off, pitch = TRACKS[lay]
        ai = 0 if axis == "x" else 1
        res = {}
        n = 0
        for p in pins:
            if p["layer"] != lay:
                continue
            n += 1
            g = nm(origin_um[ai]) + nm(offset_um[ai]) + nm(p[axis])
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
            if hc.get("orient", "R0") != "R0":
                rows.append(dict(type=tname, module=hc["module"], status="NOT_R0_SKIPPED", orient=hc.get("orient")))
                continue
            pins = json.loads(pf.read_text())["pins"]
            a = audit_pins(pins, hc["origin_um"], hc.get("track_offset_um") or [0, 0], layers)
            rows.append(dict(type=tname, module=hc["module"],
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
          f"{sum(1 for r in rows if r['status'] == 'NOT_R0_SKIPPED')} non-R0 skipped")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
