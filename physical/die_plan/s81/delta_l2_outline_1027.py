#!/usr/bin/env python3
"""S81 plan event CANDIDATE 2026-10-27 (S81-CORES-R24, COORD ruling (3)): dsdv_gunit_l2 outline derived top-down.

Why: L2 r21p AUTO-GEOM FAIL (row 35878f7ecc09): fill 0.032, empty 0.911, r2r 423.5 um > 405 (132 captures), partial E
face.  The 345.6 x 172.8 outline was inherited from the old ref-tile LEF; its content (14,041 cells, 1,906 um2 placed
std-cell area of which DFF 1,091.5 / logic 172.3 / buf+inv 642.2 incl. the long N<->S band wires) is a face-register
leaf: N 1403 + S 1469 M5 pins, E 272 M4 pins, every pin registered (flop-first / flop-last; buses this leaf only
carries cross it in 2 edges, x-aligned N<->S within 13-19 um).

Derivation (no squeezing; every number from the plan / the measured r21p placement):
  W  = 345.6 kept: the gunit stack column width (L0 above, L1 / L3 are 345.6 wide, N/S buses x-aligned with L0's S
       face); the pin budget alone needs >= 1469 / 6 pins/um = 245 um of N/S face (geom_rules pin_density).
  H  = 34.56 (8 x 4.32 PG period): fill_of_free >= 0.15 (geom_rules FILL_LO) with free = (W - 8.64) x (H - 8.64):
       A_std 1,610-1,906 um2 (measured 1,906 minus most of the 642 um2 band-gap buffering) -> H <= 40.5-46.3; at
       H 34.56 fill 0.18-0.22.  Any two flops in the core area are <= (W - 8.64) + (H - 8.64) = 362.9 um apart
       -> r2r <= 405 by construction.
  origin y = 155.52: N face abuts L0's S face with the same 17.28-um channel as today (L2<->L0 link unchanged);
       x unchanged.  The freed 138.24 um under L2 is left to the gunit layout (see NOTE).
Pins: S face unchanged; N face y -= 138.24 (same face offset); E face: the 272 pins keep their order and M4 layer,
re-spread evenly at 0.096 um (2 M4 tracks, phase 0.012) centred on the new 34.56-um face -> 10.4 pins/um, the same
pin_density WARN class as today's 10.5 (6/um would need a 45-um face, which breaks fill >= 0.15).
NOTE (not changed here): the gunit stack was designed L0 / L2 / L1 / L3 top-down (dsdv_gunit.sv header) and L2's S
face (rs/cws/rct/dl, 1,460 bits) faces L1's N face; the CCONN2 1025 re-place put L1 NW of L2 (box-nearest check), so
the L2.S -> L1.N pin-to-pin Manhattan is 469-927 um today (331-789 at origin y 155.52), > 405 with no station.

LEF: unchanged (stale ref-tile view, same as the l0r refit 1025 precedent); the kit regenerates the hard view.
  python3 physical/die_plan/s81/delta_l2_outline_1027.py [--check]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PLAN = HERE / "die_plan.json"
PINS = HERE / "inputs" / "core_pins" / "dsdv_gunit_l2.json"
OLD_OUT, NEW_OUT = [345.6, 172.8], [345.6, 34.56]
OLD_ORG, NEW_ORG = [1175.04, 17.28], [1175.04, 155.52]
DY = OLD_OUT[1] - NEW_OUT[1]          # 138.24 = 2880 x 0.048
E_PITCH, E_PHASE, T = 0.096, 0.012, 0.048
BASE_PINHASH = "1389c76618a5"   # after delta_ninepins_1027
FORMATS = {"indent0": lambda d: json.dumps(d, indent=0), "indent0_nl": lambda d: json.dumps(d, indent=0) + "\n",
           "compact": lambda d: json.dumps(d), "compact_nl": lambda d: json.dumps(d) + "\n",
           "indent2_nl": lambda d: json.dumps(d, indent=2) + "\n"}


def face(p, w, h):
    d = {"W": abs(p["x"]), "E": abs(p["x"] - w), "S": abs(p["y"]), "N": abs(p["y"] - h)}
    return min(d, key=d.get)


def new_pins(pins):
    W, H = OLD_OUT
    out, east = [], []
    for p in pins:
        f = face(p, W, H)
        q = dict(p)
        if f == "N":
            q["y"] = round(p["y"] - DY, 4)
        elif f == "E":
            east.append(q)
        elif f != "S":
            raise SystemExit(f"unexpected face {f} for {p['name']}")
        out.append(q)
    east.sort(key=lambda p: (p["y"], p["name"]))
    span = (len(east) - 1) * E_PITCH
    y0 = (NEW_OUT[1] - span) / 2
    y0 = E_PHASE + round((y0 - E_PHASE) / T) * T
    for i, q in enumerate(east):
        q["y"] = round(y0 + i * E_PITCH, 4)
    if east[0]["y"] < 0.5 or east[-1]["y"] > NEW_OUT[1] - 0.5:
        raise SystemExit("E face spread does not fit")
    return out


def apply(check_only):
    d = json.loads(PLAN.read_text())
    h = next(c for c in d["partition_types"]["gunit__t1"]["hard_cores"] if c["module"] == "dsdv_gunit_l2")
    raw = PINS.read_bytes()
    pd = json.loads(raw)
    if h["outline_um"] == NEW_OUT and h["origin_um"] == NEW_ORG:
        print("already applied")
        return 0
    if h["outline_um"] != OLD_OUT or h["origin_um"] != OLD_ORG or pd["pinhash"] != BASE_PINHASH:
        raise SystemExit(f"base mismatch: outline {h['outline_um']} origin {h['origin_um']} pinhash {pd['pinhash']}")
    fmt = next((k for k in FORMATS if FORMATS[k](json.loads(raw)) == raw.decode()), None)
    if fmt is None:
        raise SystemExit("unknown pin-table serialisation")
    pd["pins"] = new_pins(pd["pins"])
    pd["pinhash"] = hashlib.sha256(json.dumps(pd["pins"], sort_keys=True).encode()).hexdigest()[:12]
    pd["source"] += (" | S81-CORES-R24 10-27 (COORD ruling 3): outline 345.6x172.8 -> 345.6x34.56 top-down "
                     "(fill/r2r/pin-limited derivation in delta_l2_outline_1027.py), N face y -138.24, E face "
                     "re-spread 0.096 um centred, S face unchanged")
    h["outline_um"], h["origin_um"] = NEW_OUT, NEW_ORG
    # slot fit: inside the partition, no overlap with any other hard core (incl. the 17.28 channel to L0)
    pt = d["partition_types"]["gunit__t1"]
    PW, PH = pt["outline_um"]
    x0, y0 = NEW_ORG
    x1, y1 = x0 + NEW_OUT[0], y0 + NEW_OUT[1]
    assert 0 <= x0 and x1 <= PW and 0 <= y0 and y1 <= PH, "outside partition"
    for c in pt["hard_cores"]:
        if c is h:
            continue
        a0, b0 = c["origin_um"]
        a1, b1 = a0 + c["outline_um"][0], b0 + c["outline_um"][1]
        if x0 < a1 and a0 < x1 and y0 < b1 and b0 < y1:
            raise SystemExit(f"overlap with {c['inst']}")
    l0 = next(c for c in pt["hard_cores"] if c["module"] == "dsdv_gunit_l0")
    print(f"slot fit OK; channel to L0 {l0['origin_um'][1] - y1:.2f} um; new pinhash {pd['pinhash']}")
    if check_only:
        return 0
    PINS.write_text(FORMATS[fmt](pd))
    # one-line text edit of the L2 hard-core row (the file is hand-compacted; re-serialising would churn it)
    t = PLAN.read_text()
    old = '"origin_um":[1175.04,17.28],"outline_um":[345.6,172.8]'
    new = '"origin_um":[1175.04,155.52],"outline_um":[345.6,34.56]'
    row = '"module":"dsdv_gunit_l2","lef":"physical/ref_tile/dsdv_gunit_l2/views/dsdv_gunit_l2/dsdv_gunit_l2.lef",'
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
