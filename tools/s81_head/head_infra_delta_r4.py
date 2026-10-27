#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-4 PLAN-DELTA for D-INFRA-FIRST-HEAD (COORD RULING INFRA-FIRST-HEAD-3 ASK1, 2026-10-27 02:57).

1. hd_tile partition island = the tile CHANNEL CROSS (354.24, 354.24) (clock.tap_um; replaces (354.24, 518.4)):
   the mesh driver of every tile sits there (R3 tree).
2. Clock SLOTS declared per partition type: clock.die_islands_um = one 8.64-um square centred on every die tree node /
   leg repeater / mesh driver site of the R3 channel-row tree (head_slot_census.py), UNION over the type's instances
   (type hardened once, identical per replica): hd_tile channel-row slots (tile y 354.24), hd_spn / hd_spn_end spine
   slots, station-type slot rows (type y 613.44).  Refused if any slot overlaps a hard core of its type.
3. PG grid (optional --pg M8W@P,M9W@P): die.pg.grid core rows replaced (PHY domains untouched).
Pure plan edit; prints a JSON report; writes OUT.
  head_infra_delta_r4.py PLAN SLOT_CENSUS.json OUT [--pg 0.48@4.32,6.48@34.56]"""
import argparse, hashlib, json
from pathlib import Path

SIDE = 8.64
CH_CROSS = [354.24, 354.24]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("census"); ap.add_argument("out")
    ap.add_argument("--pg", help="M8 w@pitch,M9 w@pitch (offset = pitch/2, nets VDD/VSS)")
    a = ap.parse_args()
    P = json.loads(Path(a.plan).read_text())
    C = json.loads(Path(a.census).read_text())
    T = P["partition_types"]
    rep = dict(plan_in=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()[:8], types={})
    old = T["hd_tile"]["clock"].get("tap_um")
    T["hd_tile"]["clock"]["tap_um"] = CH_CROSS
    rep["hd_tile_tap_um"] = dict(old=old, new=CH_CROSS)
    bad = []
    for tn, v in C["types"].items():
        t = T[tn]
        cores = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
                  h["origin_um"][1] + h["outline_um"][1]) for h in t.get("hard_cores", []) or []]
        w, h = t["outline_um"]
        rects = []
        for s in v["slots"]:
            x, y = s["xy"]
            # NOT clipped at the type outline: a slot on an abutment edge is centred on its site (island_lattice
            # measures centre displacement); the part outside the outline lies in the abutting partition's own slot
            r = [round(x - SIDE / 2, 3), round(y - SIDE / 2, 3), round(x + SIDE / 2, 3), round(y + SIDE / 2, 3)]
            for k in cores:
                if r[0] < k[2] and k[0] < r[2] and r[1] < k[3] and k[1] < r[3]:
                    bad.append((tn, r, k))
            rects.append(r)
        t.setdefault("clock", {})["die_islands_um"] = rects
        rep["types"][tn] = dict(slots=len(rects), rows_y=v["rows_y"][:12], area_frac=round(len(rects) * SIDE * SIDE / (w * h), 5))
    if bad:
        print(json.dumps(dict(error="slot overlaps hard core", examples=bad[:10])))
        return 1
    if a.pg:
        m8, m9 = a.pg.split(",")
        g = P["die"]["pg"]["grid"]
        for L, spec in (("M8", m8), ("M9", m9)):
            w_, p_ = (float(v) for v in spec.split("@"))
            for row in g:
                if row["layer"] == L and not row.get("region"):
                    row.update(width_um=w_, pitch_um=p_, offset_um=round(p_ / 2, 3))
        rep["pg_grid"] = g
    Path(a.out).write_text(json.dumps(P, indent=1) + "\n")
    rep["plan_out"] = hashlib.sha256(Path(a.out).read_bytes()).hexdigest()[:8]
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
