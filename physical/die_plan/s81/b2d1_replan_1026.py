#!/usr/bin/env python3
"""PATH-S81-R2 D-S81-B2 item 1 (10-26): structural re-plan of the two GEOM-REVIEW-15 FAIL types of the B2 PHY-fit plan.

gunit__t1_phy1026_gunit (FAIL reach): the 10 hard cores sat in the S half while every data bus (xtier_i0/i1,
xtier_o0/o1, unit_i0) moved to the N face with the die re-lay -> pin-reg -> core hops 561-700 um.  Fix = mirror the
whole core block about the partition's horizontal centre line (orient MX, y' = H - y - h), so the cores abut the N bus
face; B2D1_GUNIT_MODE=R180 also mirrors x (puts u_l3/u_l5/u_l2 under the xtier/unit windows at x 688-1015).  Every core<->core distance is unchanged (rigid mirror).  Origins are snapped to the plan lattice (8.64) where
a core height is a half-lattice multiple, keeping >= 8.64-um channels; track_offset_um is re-solved per core so every
off-M1 pin stays on the plan tracks in the MX frame.  The early core clock tap is mirrored with its core.  FT slots
(face windows unchanged) are re-allocated with the same ft_corridor.place_slot the PHY-fit allocation used, against
the mirrored core boxes, starting at the old station count (extra stations, if any, are recorded as priced cycles).

bk_sel__t2_phy1026_bk_sel: NOT changed here (geometry needs a tile re-aspect or a slot change; see the D-S81-B2 note),
only its core connectivity is declared so G0C checks it instead of skipping.

core_conns: emits entries for both variant types from inputs/core_conns_derived.json with the same mapping as
gen_plan_v4.derived_core_conns (PF_PORT_BUS), so G0C's face rule and R3-internal reach check cover them.

usage: b2d1_replan_1026.py REPO PLAN_IN PLAN_OUT CONNS_IN CONNS_OUT LEDGER
"""
import copy
import json
import math
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
PLAN_IN, PLAN_OUT, CONNS_IN, CONNS_OUT, LEDGER = map(Path, sys.argv[2:7])
sys.path[:0] = [str(REPO), str(REPO / "tools" / "die_plan"), str(REPO / "physical" / "die_plan" / "s81")]
import numpy as np  # noqa: E402
import ft_corridor as F  # noqa: E402
import check as C  # noqa: E402

GU, BK = "gunit__t1_phy1026_gunit", "bk_sel__t2_phy1026_bk_sel"
G = 8.64
raw = json.loads(PLAN_IN.read_text())
plan_dir = REPO / "physical" / "die_plan" / "s81"
T = raw["partition_types"]
led = dict(mode=__import__("os").environ.get("B2D1_GUNIT_MODE", "MX"), tool="physical/die_plan/s81/b2d1_replan_1026.py", plan_in=str(PLAN_IN.name), gunit={}, core_conns={})


def layers():
    P = F.S.Plan(raw, PLAN_IN)
    return P.layers


LAY = layers()


def solve_offset(hc, o, ox_new, oy_new):
    """sub-lattice track offsets that put every off-M1 pin on the plan tracks in the type frame (each axis)."""
    cw, ch = hc["outline_um"]
    pins = C.core_pins(hc, plan_dir)
    res = []
    for axis, d in ((0, "V"), (1, "H")):
        pp = [(ln, (x, y)) for _n, ln, x, y in pins if ln in LAY and ln != "M1" and LAY[ln]["dir"] == d]
        base = (ox_new, oy_new)[axis]
        for k in range(0, int(round(F.S.BASE_LATTICE_UM / 0.001))):
            dd = round(k * 0.001, 3)
            if all(C.on_track(base + dd + C._orient_pt(o, cw, ch, *xy)[axis], LAY[ln]) for ln, xy in pp):
                res.append(dd)
                break
        else:
            raise SystemExit(f"no track offset for {hc['inst']} in {o} axis {axis}")
    return res


# ------------------------------------------------------------------------------------------------ gunit MX mirror
t = T[GU]
W, H = t["outline_um"]
old_cores = copy.deepcopy(t["hard_cores"])
new = []
MODE = __import__("os").environ.get("B2D1_GUNIT_MODE", "MX")      # MX (mirror y) or R180 (mirror x and y)
COMPOSE = {("R0", "MX"): "MX", ("R0", "R180"): "R180"}
for hc in t["hard_cores"]:
    ox, oy = hc["origin_um"]
    cw, ch = hc["outline_um"]
    y = H - oy - ch
    ys = round(math.floor(y / G + 1e-9) * G, 4)     # snap down to the lattice (half-lattice heights)
    x = W - ox - cw if MODE == "R180" else ox
    xs = round(math.floor(x / G + 1e-9) * G, 4)
    hc["origin_um"] = [xs, ys]
    hc["orient"] = COMPOSE[(hc.get("orient", "R0"), MODE)]
    hc["track_offset_um"] = solve_offset(hc, hc["orient"], xs, ys)
    new.append(dict(inst=hc["inst"], origin_from=[ox, oy], origin_to=hc["origin_um"], snap_um=[round(x - xs, 4),
                    round(y - ys, 4)], orient=hc["orient"], track_offset_um=hc["track_offset_um"]))
# channel check: every pair of cores >= 8.64 um apart or disjoint in the other axis (unchanged by a rigid mirror
# except where the snap moved one core)
boxes = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
          h["origin_um"][1] + h["outline_um"][1], h["inst"]) for h in t["hard_cores"]]
tight = []
for i, a in enumerate(boxes):
    for b in boxes[i + 1:]:
        gx = max(b[0] - a[2], a[0] - b[2])
        gy = max(b[1] - a[3], a[1] - b[3])
        if gx < G - 1e-6 and gy < G - 1e-6:
            tight.append((a[4], b[4], round(gx, 3), round(gy, 3)))
if tight:
    raise SystemExit(f"core channels < 8.64 after the mirror/snap: {tight}")
led["gunit"]["cores"] = new
for tp in t["clock"].get("taps", []):
    if tp.get("kind") == "core":
        hc = next(h for h in t["hard_cores"] if h["inst"] == tp["name"])
        oc = next(h for h in old_cores if h["inst"] == tp["name"])
        x, y = tp["xy"]
        # mirror about the core's own (old) box, then translate to the new box (absorbs the lattice snap)
        ny = hc["origin_um"][1] + (oc["outline_um"][1] - (y - oc["origin_um"][1]))
        nx = hc["origin_um"][0] + (oc["outline_um"][0] - (x - oc["origin_um"][0])) if MODE == "R180" else x
        led["gunit"].setdefault("core_taps", []).append(dict(name=tp["name"], xy_from=[x, y],
                                                             xy_to=[round(nx, 4), round(ny, 4)]))
        tp["xy"] = [round(nx, 4), round(ny, 4)]

# ------------------------------------------------------------------------------------------------ gunit FT re-place
model = F.S.Plan(raw, PLAN_IN)
pins = {(b, i): (x, y) for b, i, ln, x, y, d in F.type_pins(model, GU)}
cboxes = []
for c in t["hard_cores"]:
    x, y = c["origin_um"]
    cw, ch = c["outline_um"]
    dx, dy = c.get("track_offset_um", [0, 0])
    cboxes.append((x + dx - F.KEEPOFF, y + dy - F.KEEPOFF, x + dx + cw + F.KEEPOFF, y + dy + ch + F.KEEPOFF))
alloc = F.RowAllocator((4.32, 4.32, W - 4.32, H - 4.32), blocked=cboxes, cell_size=F.CELL, column_pitch=2.16,
                       row_pitch=.27, origin=(4.32, 4.32))
rows = []
for slot in sorted(t["ft_slots"], key=lambda s: -s["width"]):
    width = slot["width"] + 1
    aa = np.array([pins[(slot["name"] + "_i", i)] for i in range(width)])
    bb = np.array([pins[(slot["name"] + "_o", i)] for i in range(width)])
    start = slot["stations"]
    used = set(alloc.used)
    last = None
    for extra in range(6):
        slot["stations"] = start + extra
        alloc.used = set(used)
        try:
            sites, cents, path, ledger = F.place_slot(slot, aa, bb, slot["in_face"], slot["out_face"], W, H, cboxes,
                                                      alloc, 405 * .98 - 2)
        except (ValueError, F.NoChain) as exc:
            last = str(exc)
            continue
        slot["regs_um"] = [aa.mean(axis=0).round(4).tolist()] + [c_.round(4).tolist() for c_ in cents]
        slot["bit_site_cell_um"] = list(F.CELL)
        slot["bit_sites_um"] = [(p_ - np.array([F.CELL[0] / 2, F.CELL[1] / 2])).round(6).tolist() for p_ in sites]
        ledger.update(slot=slot["name"], old_stations=start, final_stations=slot["stations"])
        rows.append(ledger)
        break
    else:
        raise SystemExit(f"FT slot {slot['name']}: no chain ({last})")
led["gunit"]["ft_slots"] = rows
t["note"] = t.get("note", "") + "; PATH-S81-R2 D-S81-B2 10-26: core block MX-mirrored to the N bus face, FT re-allocated"

# ------------------------------------------------------------------------------------------------ core_conns sidecar
import gen_plan_v4 as GP  # noqa: E402
GP.CORE_CONNS_OUT.clear()
GP.derived_core_conns({GU: T[GU], BK: T[BK]})
conns = json.loads(CONNS_IN.read_text())
for tn, ent in GP.CORE_CONNS_OUT.items():
    conns[tn] = ent
    led["core_conns"][tn] = {ci: sorted(p) for ci, p in ent.items()}
CONNS_OUT.write_text(json.dumps(conns, indent=1, sort_keys=True) + "\n")
PLAN_OUT.write_text(json.dumps(raw, separators=(",", ":")) + "\n")
LEDGER.write_text(json.dumps(led, indent=1) + "\n")
print("gunit cores", len(new), "ft slots", [(r["slot"], r["old_stations"], r["final_stations"]) for r in rows])
print("core_conns types", list(GP.CORE_CONNS_OUT))
