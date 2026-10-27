#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-4 PLAN-DELTA for D-INFRA-FIRST-HEAD (COORD RULING INFRA-FIRST-HEAD-3 ASK1, 2026-10-27 02:57).

1. hd_tile partition island = the tile CHANNEL CROSS (354.24, 354.24) (clock.tap_um; replaces (354.24, 518.4)):
   the mesh driver of every tile sits there (R3 tree).
2. Clock SLOTS declared per partition type: clock.die_islands_um = one 8.64-um square centred on every die tree node /
   (HEAD-R17: centre clamped inside the type outline, snap_inside; reported as site_moves)
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


def snap_inside(x, y, w, h):
    """HEAD-R17 (ROOT-MERGE-32): an island is a pushdown reservation of ONE partition netlist (12.2a1), so it lies
    inside the type outline BY CONSTRUCTION.  A site on (or within SIDE/2 of) an abutment edge -- the binary merge of
    two adjacent tile drivers lands exactly on the shared tile edge -- gets its island centre clamped to
    [SIDE/2, W-SIDE/2] x [SIDE/2, H-SIDE/2]; the move (<= SIDE/2 per axis) is reported per type as site_moves: the
    tree generator must put that node / leg repeater / driver on the island centre (island_lattice displacement 0)."""
    lo = SIDE / 2
    if w < SIDE or h < SIDE:
        raise SystemExit(f"type outline {w}x{h} smaller than one {SIDE}-um island")
    return round(min(max(x, lo), w - lo), 3), round(min(max(y, lo), h - lo), 3)


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
        rects, moves = [], []
        for s in v["slots"]:
            x, y = s["xy"]
            cx, cy = snap_inside(x, y, w, h)
            if (cx, cy) != (round(x, 3), round(y, 3)):
                moves.append(dict(site=[x, y], island_centre=[cx, cy], disp_um=round(abs(cx - x) + abs(cy - y), 3),
                                  roles=s.get("roles")))
            r = [round(cx - SIDE / 2, 3), round(cy - SIDE / 2, 3), round(cx + SIDE / 2, 3), round(cy + SIDE / 2, 3)]
            for k in cores:
                if r[0] < k[2] and k[0] < r[2] and r[1] < k[3] and k[1] < r[3]:
                    bad.append((tn, r, k))
            if r not in rects:
                rects.append(r)
        t.setdefault("clock", {})["die_islands_um"] = rects
        rep["types"][tn] = dict(slots=len(rects), rows_y=v["rows_y"][:12], area_frac=round(len(rects) * SIDE * SIDE / (w * h), 5),
                                snapped=len(moves), max_snap_um=max((m["disp_um"] for m in moves), default=0.0),
                                site_moves=moves)
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
    Path(a.out).write_text(json.dumps(P, indent=2) + "\n")
    rep["plan_out"] = hashlib.sha256(Path(a.out).read_bytes()).hexdigest()[:8]
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
