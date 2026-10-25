#!/usr/bin/env python3
"""Re-pin one HBM core kit view from a new face pin table, keeping RTL / recipe / flow identical (PATH-HBM 2026-10-25).

    python3 physical/die_plan/hbm_arch_cores/kit_pins_regen.py --views VIEWS.json --view VIEW --pins NEW_PINS.json \
        --out-views OUT/views_repin.json [--check-same-names]

NEW_PINS.json = list of {bus, bit, layer, x, y, face} (the parent pin-assignment format, e.g. tkm_tile_pins.json; bit
null = scalar).  It is converted to the plan pin-file format ({name, layer, x, y}; edge coordinate inset 0.019 um as
the plan exporter writes it: N y = H - 0.019, S y = 0.019, E x = W - 0.019, W x = 0.019) next to OUT views, and a
one-view copy of VIEWS with pins_file (absolute) / pins_sha256 / pins replaced is written.  The pin NAME SET must equal
the old pin file's (a re-pin never adds or drops a port); the lattice check stays in gen_core_kit_hbm.py.  Then
regenerate the kit with gen_core_kit_hbm.py --views OUT/views_repin.json --view VIEW (same options as before).
"""
import argparse, hashlib, json, sys
from pathlib import Path

INSET = 0.019


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--views", required=True)
    ap.add_argument("--view", required=True)
    ap.add_argument("--pins", required=True)
    ap.add_argument("--out-views", required=True)
    ap.add_argument("--port-change", action="store_true",
                    help="the RTL port list changed with this table (new ports, e.g. tile_clr_o / tile_conv_o): the name "
                         "set may differ; the generator's port-bind gate checks pins against the RTL")
    a = ap.parse_args()
    V = json.load(open(a.views))
    v = next((x for x in V["view_list"] if x["view"] == a.view), None)
    if not v:
        raise SystemExit(f"view {a.view} not in {a.views}")
    plan = Path(V["plan"])
    if not plan.is_absolute():
        plan = (Path(a.views).resolve().parent / plan).resolve()
    old = json.load(open(plan.parent / v["pins_file"]))
    w, h = v["outline_um"]
    new = []
    for q in json.load(open(a.pins)):
        name = q["bus"] if q.get("bit") is None else f"{q['bus']}[{q['bit']}]"
        x, y, f = float(q["x"]), float(q["y"]), q["face"]
        if f == "N":
            y = round(h - INSET, 3)
        elif f == "S":
            y = INSET
        elif f == "E":
            x = round(w - INSET, 3)
        elif f == "W":
            x = INSET
        else:
            raise SystemExit(f"{name}: face {f!r}")
        new.append(dict(name=name, layer=q["layer"], x=round(x, 3), y=round(y, 3)))
    on, nn = {p["name"] for p in old}, [p["name"] for p in new]
    if len(set(nn)) != len(nn):
        raise SystemExit("duplicate pin names in the new table")
    if set(nn) != on and not a.port_change:
        raise SystemExit(f"pin name set differs: missing {sorted(on - set(nn))[:5]} extra {sorted(set(nn) - on)[:5]}")
    out = Path(a.out_views).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    pf = out.parent / (v["module"] + "__repin.json")
    pf.write_text(json.dumps(new, indent=0) + "\n")
    nv = dict(v, pins_file=str(pf), pins_sha256=sha(pf), pins=len(new), repin_src=dict(file=str(Path(a.pins).resolve()),
                                                                                  sha256=sha(a.pins)))
    W = dict(V, plan=str(plan), view_list=[nv], views=1)
    out.write_text(json.dumps(W, indent=1) + "\n")
    print(json.dumps(dict(added=sorted(set(nn) - on), removed=sorted(on - set(nn)))))
    moved = sum(1 for p, o in zip(sorted(new, key=lambda p: p["name"]), sorted(old, key=lambda p: p["name"]))
                if (p["layer"], p["x"], p["y"]) != (o["layer"], o["x"], o["y"]))
    print(json.dumps(dict(view=a.view, pins=len(new), moved=moved, pins_file=str(pf), views=str(out))))


if __name__ == "__main__":
    sys.exit(main())
