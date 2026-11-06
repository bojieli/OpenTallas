#!/usr/bin/env python3
"""KV-PRMSLOT-1 11-06: KV plan SLOT EVENT, hard core qkd_hr_core_prompt 233.28 -> 254.88 um square (COORD 12:2x (3)).

Form = the DIE-KV-40 q1/q2 widen: origin fixed (319.68, 380.16 in kv3_hub_Wi), the core grows toward the free
space (east and north). Pin table = the transform of the KV-PRM-B4 vB kit (grow_outline.py, sha256 50c1797368ffefa3)
applied to the plan pins (centre form, 0.096 inward): coords >= 231.78 shift +21.6 (E/N faces stay on the edge),
coords <= 1.5 kept (W/S), all others x 254.88/233.28 snapped to 0.048. Faces and pin order unchanged. The plan pins then
equal the vB kit pins.json (edge form) pin for pin, so the vB/vC sign-off counts against this plan.
The only plan object the grown slot covers is ft24 station 3 (145 bit sites x 572.4/574.56, y 419-441, reg
574.32,430.57) in the old 34.56-um prompt/rx street; it moves east by 8.64 (one die grid) to the street centre column
x 581.04/583.2 (the same columns ft6 station 1 already uses north of rx). Hops to ft24 stations 2/4 get shorter.
Clock tap host__qkd_hr_core_prompt.ck[0] follows the core ck[0] pin (insertion numbers unchanged, proxy view).
usage: prmslot_event.py PLAN_DIR [--on-track]
--on-track: the scaled pins snap to the M4/M5 track phase (0.024 + k*0.048) instead of k*0.048. The plain vB transform
puts 4745 of 5124 pins between tracks (G0C hard_cores ERROR); --on-track moves each of them by <= 0.024 um.
"""
import json
import sys
from pathlib import Path

TYPE, INST = "kv3_hub_Wi", "host__qkd_hr_core_prompt"
OLD, NEW = 233.28, 254.88
S, D = NEW / OLD, round(NEW - OLD, 3)
PINS_OLD = "pins/qkd_hr_core_prompt_pins_r26q5.json"
PINS_NEW = "pins/qkd_hr_core_prompt_pins_r26q5_g255" + ("t" if "--on-track" in sys.argv else "") + ".json"
FT, FT_STATION, FT_DX = "ft24", 3, 8.64
TAG = "KV-PRMSLOT-1 11-06"
ON_TRACK = "--on-track" in sys.argv  # snap scaled pins to the 0.024-phase M4/M5 tracks (G0C hard_cores track rule)


TRK = {"M4": (0.024, 0.048), "M5": (0.024, 0.048), "M6": (0.032, 0.064), "M7": (0.032, 0.064)}


def m(v, layer="M5"):
    """grow_outline.py m() (KV-PRM-B4 vB kit transform), same constants."""
    v = float(v)
    if v >= OLD - 1.5:
        return round(v + D, 3)
    if v <= 1.5:
        return v
    if ON_TRACK:  # plan + kit tracks (make_tracks, track_offset [0, 0]): M4/M5 0.024+k*0.048, M6/M7 0.032+k*0.064
        off, pitch = TRK[layer]
        return round(off + round((v * S - off) / pitch) * pitch, 3)
    return round(round(v * S / 0.048) * 0.048, 3)


def main():
    pd = Path(sys.argv[1])
    plan = json.loads((pd / "plan_c.json").read_text())
    t = plan["partition_types"][TYPE]
    (hc,) = [h for h in t["hard_cores"] if h["inst"] == INST]
    assert hc["outline_um"] == [OLD, OLD] and hc["pins_file"] == PINS_OLD and hc["orient"] == "R0", hc
    ox, oy = hc["origin_um"]
    pins = json.loads((pd / PINS_OLD).read_text())
    for p in pins["pins"]:
        p["x"], p["y"] = m(p["x"], p["layer"]), m(p["y"], p["layer"])
    pins["frame"] = f"core R0, origin (0,0), outline {NEW} x {NEW}"
    pins["source"] += (f" | {TAG} slot event: outline {OLD} -> {NEW} (KV-PRM-B4 vB grow_outline.py transform, sha256 "
                       "50c1797368ffefa3: >=231.78 +21.6, <=1.5 kept, else x254.88/233.28 snap " + ("onto the layer tracks (M4/M5 0.024+k*0.048, M7 0.032+k*0.064)" if ON_TRACK else "0.048") + "; faces/order unchanged)")
    (pd / PINS_NEW).write_text(json.dumps(pins, indent=1) + "\n")
    ck = [p for p in pins["pins"] if p["name"] == "ck[0]"][0]
    hc["outline_um"] = [NEW, NEW]
    hc["pins_file"] = PINS_NEW
    hc["note"] += (f" | {TAG}: SLOT EVENT outline {OLD} -> {NEW} (origin fixed, grows E+N; COORD 11-06 12:2x (3), "
                   "KV-PRM-B4/B5 vB/vC kit = this pin table)")
    taps = [tp for tp in t["clock"]["taps"] if tp["name"] == INST + ".ck[0]"]
    assert len(taps) == 1
    old_tap = list(taps[0]["xy"])
    taps[0]["xy"] = [round(ox + ck["x"], 3), round(oy + ck["y"], 3)]
    taps[0]["note"] += f" | {TAG}: xy follows ck[0] of the {NEW} slot ({old_tap} -> {taps[0]['xy']}); insertion unchanged"
    (ft,) = [s for s in t["ft_slots"] if s["name"] == FT]
    st_sites = ft["bit_sites_um"][FT_STATION - 1]
    xs = sorted({q[0] for q in st_sites})
    assert xs == [572.4, 574.56], xs
    for q in st_sites:
        q[0] = round(q[0] + FT_DX, 3)
    r = ft["regs_um"][FT_STATION]
    assert abs(r[0] - 574.3235) < 1e-3, r
    r[0] = round(r[0] + FT_DX, 4)
    # top-level plan note left as is (KV-SYSSD-2 edits the same plan in parallel; record in prmslot_1106/README.md)
    (pd / "plan_c.json").write_text(json.dumps(plan, indent=1) + "\n")
    print(json.dumps(dict(origin=[ox, oy], outline=[NEW, NEW], pins=len(pins["pins"]), ck=[ck["x"], ck["y"]],
                          tap=[old_tap, taps[0]["xy"]], ft24_st3_sites=len(st_sites), ft24_reg=r)))


if __name__ == "__main__":
    main()
