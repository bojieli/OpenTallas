#!/usr/bin/env python3
"""S81 plan event CANDIDATE 2026-10-27 (S81-CORES-R27, GEOM-REVIEW-34 verdict on AUTO-GEOM a0a7e556d757):
dsdv_gunit_l2 outline 345.6 x 34.56 -> 345.6 x 43.2 (one 8.64 lattice row taller), origin unchanged.

Why: the r26 kit (gunit plan event pins) placed at 34.56 and failed AUTO-GEOM: 50-it GRT M2-M5 adj 0.25 overflow 137
(M2 55 + M4 82), every congested gcell +1 track, all at x 170-200 (the bisection column of the 345.6-um strip) on the
two horizontal layers; M3 25.8 % and M5 4.7 % used.  GEOM-REVIEW-34: FAIL STRUCTURAL (height over-cut), fix = height
43.2-51.84 (the GEOM-31 range).  34.56 gives 2 x 34.56/0.048 H tracks across the cut; 43.2 adds +25 %, against a
measured ~6 % (1 of 16-19 tracks) shortfall.  43.2 is the smallest lattice step in the reviewed range: fill stays as
high as possible (the R24 fill derivation put H <= 40.5-46.3 for fill_of_free >= 0.15).
Geometry: origin (1019.52, 613.44) kept, so the S face (L1.N bundle, 1734 pins) is byte-identical; the N face (1403
pins, L0.N bundle) moves +8.64 with the outline; E face (7 M4 pins at y 19.6-30.3) unchanged (inside 43.2).  The strip
y 648.0-656.64 x 1019.52-1365.12 is empty in gunit__t1 (no hard core, station, ft slot, clock tap; checked below).
LEF: unchanged (stale ref-tile view, l2_outline / l0r refit precedent); the kit regenerates the hard view.
NOT done here (GEOM-REVIEW-34 second item): even spread of each N/S bus over the full face; the bundles stay in the
R25 partner-x order (r2r 339.3, 0 > 405).
  python3 physical/die_plan/s81/delta_l2_h432_1027.py [--check]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "die_plan.json"
PINS = HERE / "inputs" / "core_pins" / "dsdv_gunit_l2.json"
ORG = [1019.52, 613.44]
OLD_OUT, NEW_OUT = [345.6, 34.56], [345.6, 43.2]
DY = round(NEW_OUT[1] - OLD_OUT[1], 4)          # 8.64 = 180 x 0.048
BASE_PINHASH = "27b9b0c4a6eb"                   # after delta_gunit_relayout_1027 (R25/R26)
FORMATS = {"indent0": lambda d: json.dumps(d, indent=0), "indent0_nl": lambda d: json.dumps(d, indent=0) + "\n",
           "compact": lambda d: json.dumps(d), "compact_nl": lambda d: json.dumps(d) + "\n",
           "indent1_nl": lambda d: json.dumps(d, indent=1) + "\n", "indent2_nl": lambda d: json.dumps(d, indent=2) + "\n"}


def face(p, w, h):
    d = {"W": abs(p["x"]), "E": abs(p["x"] - w), "S": abs(p["y"]), "N": abs(p["y"] - h)}
    return min(d, key=d.get)


def new_pins(pins):
    W, H = OLD_OUT
    out, n = [], {"N": 0, "S": 0, "E": 0}
    for p in pins:
        f = face(p, W, H)
        if f not in n:
            raise SystemExit(f"unexpected face {f} for {p['name']}")
        q = dict(p)
        if f == "N":
            q["y"] = round(p["y"] + DY, 4)
        elif f == "E" and not (0.5 < p["y"] < NEW_OUT[1] - 0.5):
            raise SystemExit(f"E pin {p['name']} outside the new face")
        n[f] += 1
        out.append(q)
    for q in out:   # faces must be unambiguous in the new outline too
        f0 = face(q, *NEW_OUT)
        if f0 != face(next(p for p in pins if p["name"] == q["name"]), *OLD_OUT):
            raise SystemExit(f"pin {q['name']} changes face")
    return out, n


def apply(check_only):
    d = json.loads(PLAN.read_text())
    pt = d["partition_types"]["gunit__t1"]
    h = next(c for c in pt["hard_cores"] if c["module"] == "dsdv_gunit_l2")
    raw = PINS.read_bytes()
    pd = json.loads(raw)
    if h["outline_um"] == NEW_OUT and h["origin_um"] == ORG:
        print("already applied")
        return 0
    if h["outline_um"] != OLD_OUT or h["origin_um"] != ORG or pd["pinhash"] != BASE_PINHASH:
        raise SystemExit(f"base mismatch: outline {h['outline_um']} origin {h['origin_um']} pinhash {pd['pinhash']}")
    fmt = next((k for k in FORMATS if FORMATS[k](json.loads(raw)) == raw.decode()), None)
    if fmt is None:
        raise SystemExit("unknown pin-table serialisation")
    pd["pins"], n = new_pins(pd["pins"])
    pd["pinhash"] = hashlib.sha256(json.dumps(pd["pins"], sort_keys=True).encode()).hexdigest()[:12]
    pd["source"] += (" | S81-CORES-R27 10-27 (GEOM-REVIEW-34 a0a7e556d757 height over-cut): outline 345.6x34.56 -> "
                     "345.6x43.2, origin kept, N face y +8.64, S/E faces unchanged (delta_l2_h432_1027.py)")
    h["outline_um"] = NEW_OUT
    PW, PH = pt["outline_um"]
    x0, y0 = ORG
    x1, y1 = x0 + NEW_OUT[0], y0 + NEW_OUT[1]
    assert 0 <= x0 and x1 <= PW and 0 <= y0 and y1 <= PH, "outside partition"
    for c in pt["hard_cores"]:
        if c is h:
            continue
        a0, b0 = c["origin_um"]
        a1, b1 = a0 + c["outline_um"][0], b0 + c["outline_um"][1]
        if x0 < a1 and a0 < x1 and y0 < b1 and b0 < y1:
            raise SystemExit(f"overlap with {c['inst']}")
    # nothing else of the partition type (stations, ft slots, clock taps, bus windows) inside the grown strip
    strip = (x0, y0 + OLD_OUT[1], x1, y1)
    hits = []

    def scan(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                scan(v, f"{p}.{k}")
        elif isinstance(o, list):
            if len(o) == 2 and all(isinstance(v, (int, float)) for v in o):
                if strip[0] < o[0] < strip[2] and strip[1] < o[1] < strip[3]:
                    hits.append((p, o))
            elif len(o) == 4 and all(isinstance(v, (int, float)) for v in o):
                if o[0] < strip[2] and o[2] > strip[0] and o[1] < strip[3] and o[3] > strip[1]:
                    hits.append((p, o))
            else:
                for i, v in enumerate(o):
                    scan(v, f"{p}[{i}]")
    scan({k: v for k, v in pt.items() if k != "hard_cores"}, "gunit__t1")
    if hits:
        raise SystemExit(f"grown strip not empty: {hits[:5]}")
    print(f"slot fit OK (strip {strip} empty); pins N {n['N']} (+{DY}) S {n['S']} E {n['E']}; new pinhash {pd['pinhash']}")
    if check_only:
        return 0
    PINS.write_text(FORMATS[fmt](pd))
    t = PLAN.read_text()
    row = '"module":"dsdv_gunit_l2","lef":"physical/ref_tile/dsdv_gunit_l2/views/dsdv_gunit_l2/dsdv_gunit_l2.lef",'
    old = '"origin_um":[1019.52,613.44],"outline_um":[345.6,34.56]'
    new = '"origin_um":[1019.52,613.44],"outline_um":[345.6,43.2]'
    i = t.index(row)
    if t.count(row) != 1 or t.find(old, i) != i + len(row):
        raise SystemExit("die_plan.json L2 row text not as expected")
    t = t[:i + len(row)] + new + t[i + len(row) + len(old):]
    if json.loads(t) != d:
        raise SystemExit("text edit != intended plan")
    PLAN.write_text(t)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    sys.exit(apply(ap.parse_args().check))
