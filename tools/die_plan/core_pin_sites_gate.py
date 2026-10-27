#!/usr/bin/env python3
"""Plan pin-site gate for hard-core pin tables (S81-CORE-LAT-R6, COORD RULING 2026-10-26 15:12: core pins come from the
top-down plan pin assignment and are never stacked; the gate must fail stacked / duplicate pin sites).

Checks every hard core of a die plan (die_plan.json partition_types[*].hard_cores[*] with a pins_file), each distinct
pins_file once, against its plan outline_um:
  dup_site      two or more pins with the same (layer, x, y) centre                       -> FAIL
  pitch         two pins on the same face + layer closer than MIN_PITCH along the face     -> FAIL
                (centre-to-centre; one ASAP7 routing track: M2/M3 0.036, M4/M5 0.048, M6/M7 0.064 um -- two pins
                 on one track at one face position is the GRT-0031 / GRT-0080 'Invalid pin placement' abort)
  dup_name      the same pin name twice                                                     -> FAIL
  off_face      pin centre farther than FACE_TOL (2.5 um) from every outline face          -> FAIL
                (plan tables extracted from LEF carry the access-extension centre up to ~1.2 um inside; the kit
                 snaps those onto the face, so the along-face coordinate is what is checked)
  off_outline   pin centre outside [0, W] x [0, H] along its face                           -> FAIL
Interior (face "C") clock-entry pins are the plan's island entry (12.8a) and are skipped by the face checks, but take
part in dup_site/dup_name.
usage: python3 -I core_pin_sites_gate.py DIE_PLAN.json [--pins-root DIR] [--module M ...] [--out OUT.json]
       python3 -I core_pin_sites_gate.py --pins PINS.json --outline W H [--out OUT.json]
exit 0 = PASS, 1 = FAIL, 2 = usage / missing file.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

MIN_PITCH = {"M2": 0.036, "M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064}
FACE_TOL = 2.5
EPS = 1e-4


def face(p, w, h):
    d = {"W": abs(p["x"]), "E": abs(p["x"] - w), "S": abs(p["y"]), "N": abs(p["y"] - h)}
    f = min(d, key=d.get)
    return f if d[f] <= FACE_TOL else "C"


def load_pins(f):
    d = json.load(open(f))
    return d["pins"] if isinstance(d, dict) else d


def check_pins(pins, w, h, interior_ok=("clk",)):
    errs = collections.defaultdict(list)
    names = collections.Counter(p["name"] for p in pins)
    for n, c in names.items():
        if c > 1:
            errs["dup_name"].append(dict(name=n, count=c))
    sites = collections.defaultdict(list)
    for p in pins:
        sites[(p["layer"], round(p["x"], 4), round(p["y"], 4))].append(p["name"])
    for (L, x, y), ns in sites.items():
        if len(ns) > 1:
            errs["dup_site"].append(dict(layer=L, x=x, y=y, pins=ns))
    rows = collections.defaultdict(list)
    for p in pins:
        f = face(p, w, h)
        if f == "C":
            if p["name"] not in interior_ok:
                errs["off_face"].append(dict(name=p["name"], x=p["x"], y=p["y"]))
            continue
        a = p["y"] if f in "WE" else p["x"]
        if a < -EPS or a > (h if f in "WE" else w) + EPS:
            errs["off_outline"].append(dict(name=p["name"], face=f, along=a))
        rows[(f, p["layer"])].append((a, (round(p["x"], 4), round(p["y"], 4)), p["name"]))
    for (f, L), r in rows.items():
        r.sort()
        mp = MIN_PITCH.get(L, 0.096)
        for (a0, s0, n0), (a1, s1, n1) in zip(r, r[1:]):
            if a1 - a0 < mp - EPS and s0 != s1:   # identical centres are reported as dup_site
                errs["pitch"].append(dict(face=f, layer=L, a=n0, b=n1, gap=round(a1 - a0, 4), min=mp))
    stacked = sorted({n for e in errs["dup_site"] for n in e["pins"]} |
                     {n for e in errs["pitch"] for n in (e["a"], e["b"])})
    return dict(pins=len(pins), counts={k: len(v) for k, v in errs.items()}, stacked_pins=len(stacked),
                verdict="FAIL" if any(errs.values()) else "PASS",
                examples={k: v[:8] for k, v in errs.items() if v})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--pins-root", default=None, help="dir the plan pins_file paths are relative to (default: plan dir)")
    ap.add_argument("--module", action="append", default=[])
    ap.add_argument("--pins")
    ap.add_argument("--outline", nargs=2, type=float)
    ap.add_argument("--out")
    a = ap.parse_args()
    rep = dict(schema="opentallas.core_pin_sites_gate.v1", min_pitch_um=MIN_PITCH, face_tol_um=FACE_TOL, cores={})
    if a.pins:
        if not a.outline:
            ap.error("--pins needs --outline W H")
        rep["cores"][a.pins] = check_pins(load_pins(a.pins), *a.outline)
    elif a.plan:
        pp = Path(a.plan)
        root = Path(a.pins_root) if a.pins_root else pp.parent
        d = json.load(open(pp))
        pts = d["partition_types"]
        pts = pts.values() if isinstance(pts, dict) else pts
        seen = {}
        for t in pts:
            for hc in t.get("hard_cores", []) or []:
                if a.module and hc["module"] not in a.module:
                    continue
                pf = hc.get("pins_file")
                if not pf:
                    continue
                key = (pf, tuple(hc["outline_um"]))
                if key in seen:
                    continue
                f = root / pf
                if not f.is_file():
                    print(f"missing pins file {f}", file=sys.stderr)
                    sys.exit(2)
                r = check_pins(load_pins(f), *hc["outline_um"])
                r.update(module=hc["module"], outline_um=hc["outline_um"])
                seen[key] = r
                rep["cores"][f"{pf}@{hc['outline_um'][0]}x{hc['outline_um'][1]}"] = r
    else:
        ap.error("give DIE_PLAN.json or --pins")
    bad = {k: v for k, v in rep["cores"].items() if v["verdict"] == "FAIL"}
    rep["verdict"] = "FAIL" if bad else "PASS"
    rep["n_cores"], rep["n_fail"] = len(rep["cores"]), len(bad)
    for k, v in rep["cores"].items():
        print(f"{v['verdict']} {k} pins {v['pins']} stacked {v['stacked_pins']} {v['counts']}")
    print(f"core_pin_sites_gate: {rep['verdict']} {len(bad)}/{len(rep['cores'])} pin tables fail")
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1) + "\n")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
