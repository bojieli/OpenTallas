#!/usr/bin/env python3
"""DIE-HEAD-30 fix-only plan delta hk5l on the frozen hk5 plan (COORD 11:09 ruling: pins not moved with the hk5 windows = FIX).
DIE-HEAD-26 hk5_tile moved the hd_tile i/o data windows 354.24-654.272 -> 708.48-1008.512 (and the tile-facing windows of
hd_turn_a / hd_turn_b / the 4 spine shims by the same +354.24), but the count-aligned landing scalars that clock_landing_plan.py
derives from the bus point (fclk_in/out, cland_fstart_in/out, cland_dn/up_ready/fault), their edge_clocks taps and the
ring storage bands were generated on hk4 and stayed at the old window (y ~504).  GEOM-59 11:12: pin -> farthest ring slot
max 339.1 um FAIL; fix = ring slots adjacent to the W face.  This script moves, on the same faces and the same frame
offsets as hk5_tile, every landing scalar/edge tap/band that sits in the OLD tile-facing window by +354.24 (0 cycles, no
RTL edit), and re-shapes the hd_tile ring band from the 99x82 W-corner block [17.28,706.32,116.64,788.4] to a W-face column
[17.28,708.48,47.52,1008.512] along the i pins (the same 30.24-um column form hd_turn_a / shims already use: spread 2.0).
Asserts the old geometry before every move.  usage: hk5_land_pins.py IN_PLAN OUT_PLAN"""
import json, sys
DY = 354.24
p = json.load(open(sys.argv[1]))
pt = p["partition_types"]
log = []
def inwin(y, lo, hi):
    return lo - 1e-6 <= y <= hi + 1e-6
# type -> (old window in the type frame, faces that face a tile)
SPEC = {"hd_tile": ([354.24, 654.272], ("W", "E")), "hd_turn_a": ([354.24, 654.272], ("W",)),
        "hd_turn_b": ([17.28, 317.312], ("W",)),
        **{t: ([354.24, 654.272], ("W", "E")) for t in ("hd_spn_eshim_tx", "hd_spn_eshim_rx", "hd_spn_wshim_tx", "hd_spn_wshim_rx")}}
LAND = ("fclk_in_", "fclk_out_", "cland_fstart_in_", "cland_fstart_out_", "cland_dn_ready_", "cland_dn_fault_",
        "cland_up_ready_", "cland_up_fault_")
for tn, (old, faces) in SPEC.items():
    t = pt[tn]; w, h = t["outline_um"]; c = t["clock"]; lc = c["landing_contract"]
    def face(x, y):
        return "W" if abs(x) < 4.4 else "E" if abs(x - w) < 4.4 else "S" if abs(y) < 4.4 else "N" if abs(y - h) < 4.4 else "I"
    moved = {}
    for q in lc["pins"]:
        if not q["name"].startswith(LAND):
            continue
        x, y = q["xy_um"]
        if face(x, y) in faces and inwin(y, *old):
            q["xy_um"] = [x, round(y + DY, 3)]; moved[q["name"]] = q["xy_um"]
            log.append(f"{tn}.{q['name']} ({x},{y}) -> {q['xy_um']}")
    for e in c.get("edge_clocks", []):
        if e["port"] in moved:
            assert e["tap_um"][0] == moved[e["port"]][0] and abs(e["tap_um"][1] + DY - moved[e["port"]][1]) < 1e-6, e
            e["tap_um"] = list(moved[e["port"]]); log.append(f"{tn}.edge_clocks.{e['port']} -> {e['tap_um']}")
    for b in t.get("buses", []):
        if b["name"] in moved and "xy_um" in b:
            b["xy_um"] = list(moved[b["name"]])
    for bus, band in lc.get("bands", {}).items():
        if ("fclk_in_" + bus) not in moved:
            continue
        r = band["rect_um"]
        if tn == "hd_tile":
            assert r == [17.28, 706.32, 116.64, 788.4], r
            nr = [17.28, 708.48, 47.52, 1008.512]
        else:
            assert inwin(r[1], *old) and inwin(r[3], old[0], old[1] + 30), (tn, r)
            nr = [r[0], round(r[1] + DY, 3), r[2], round(r[3] + DY, 3)]
            assert nr[3] <= h - 4.32 + 1e-6, (tn, nr, h)
        band["rect_um"] = nr
        band["note"] = "DIE-HEAD-30 hk5l: band follows the hk5 tile-facing window (GEOM-59 11:12 ring slots at the face)"
        log.append(f"{tn}.bands.{bus} {r} -> {nr}")
    if not moved:
        log.append(f"{tn}: no landing scalar in the old window on faces {faces}")
# every landing scalar that still sits in an old window on a tile-facing face is an error
for tn, (old, faces) in SPEC.items():
    t = pt[tn]; w, h = t["outline_um"]
    for q in t["clock"]["landing_contract"]["pins"]:
        x, y = q["xy_um"]
        if q["name"].startswith(LAND) and (abs(x) < 4.4 and "W" in faces or abs(x - w) < 4.4 and "E" in faces) and inwin(y, *old):
            raise SystemExit(f"left behind {tn}.{q['name']} {q['xy_um']}")
p["note"] = p.get("note", "") + " | DIE-HEAD-30 hk5l: landing scalars/edge taps/ring bands follow the hk5 tile windows (+354.24)"
json.dump(p, open(sys.argv[2], "w"), indent=1)
print("\n".join(log))
