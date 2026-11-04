#!/usr/bin/env python3
"""DIE-S81-51/RF-B 11-03 (S81-RF1 RE-FORM, xrt1 + xrt3): one uniform xrt template.
* ot_s81sl_xrt1 takes the xrt3 slot form: outline 207.36 x 164.16 (was 311.04 x 395.28, fill ~0.10), the xrt3 pin table
  minus the C3-only band ports bi / bo (pin names are otherwise identical, 7563 = 9122 - 1046 - 513), same layers M3-M6.
* ot_s81sl_xrt3 keeps its slot (207.36 x 164.16, fill ~0.40 with the out-face latches).
Writes inputs/core_pins/ot_s81sl_xrt1_rf1.json and a TRIAL plan copy (kit generation only; the plan event itself is
DIE-S81-51/PLAN's S81-RF1).  Usage: delta_rfb_xrt.py <plan_in> <plan_out>   (cwd = physical/die_plan/s81)"""
import json, re, sys
src, dst = sys.argv[1:3]
x3 = json.load(open("inputs/core_pins/ot_s81sl_xrt3.json"))
pins = [p for p in x3["pins"] if not re.match(r"(bi|bo)\[", p["name"])]
x1 = dict(module="ot_s81sl_xrt1", lef=x3["lef"],
          source="DIE-S81-51/RF-B 11-03 RE-FORM: uniform xrt template = inputs/core_pins/ot_s81sl_xrt3.json minus bi/bo "
                 "(C3-only band ports); outline 207.36x164.16; directions from the kit RTL (rtl_dirs)", pins=pins)
x1["pinhash"] = __import__("hashlib").sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:12]
json.dump(x1, open("inputs/core_pins/ot_s81sl_xrt1_rf1.json", "w"), indent=1)
plan = json.load(open(src)); n = 0
for t, v in plan["partition_types"].items():
    for h in v.get("hard_cores", []):
        if h["module"] == "ot_s81sl_xrt1":
            h.update(outline_um=[207.36, 164.16], pins_file="inputs/core_pins/ot_s81sl_xrt1_rf1.json", lef=x3["lef"],
                     obs_max="M6", rfb_note="RF-B 11-03 trial: xrt template (xrt3 form minus bi/bo)")
            h.pop("lib", None); n += 1
plan["note"] = (plan.get("note", "") + " | RF-B xrt trial copy 11-03 (xrt1 -> xrt template, %d instances)" % n)
json.dump(plan, open(dst, "w"), indent=1)
print("xrt1 instances re-formed", n, "pins", len(pins))
# M6 grant (gen m6_pin_grant): every xrt1 instance must see the die M6 lattice at the template's M6 pin phase.  TRIAL
# origins only: shift origin y by j * 2.16 um (lcm of the 0.27 row and the M2-M5 track pitches: other layers unchanged)
# until the phase matches; DIE-S81-51/PLAN places the real slots.
M6P, M6O = 64, 32
ph = {round(q["y"] * 1000) % M6P for q in pins if q["layer"] == "M6"}; assert len(ph) == 1, ph; ph = ph.pop()
moved = []
for t, v in plan["partition_types"].items():
    for h in v.get("hard_cores", []):
        if h["module"] != "ot_s81sl_xrt1":
            continue
        for j in range(4):
            oy = round(h["origin_um"][1] * 1000) + 2160 * j + round(h.get("track_offset_um", [0, 0])[1] * 1000)
            mir = h.get("orient", "R0") in ("MX", "R180")
            loc = (164160 + oy - M6O) % M6P if mir else (M6O - oy) % M6P
            if loc == ph:
                break
        else:
            raise SystemExit(f"{t}: no M6 phase shift")
        if j:
            h["origin_um"] = [h["origin_um"][0], round(h["origin_um"][1] + 2.16 * j, 3)]; moved.append((t, j))
json.dump(plan, open(dst, "w"), indent=1)
print("M6 phase", ph, "trial origin shifts", moved)
# appended to delta_rfb_xrt_1103.py: GEOM-21 clock pin (kit_contract.clock_pin_geometry: M5, on the M5 track,
# >= 0.048 x 0.48).  The xrt3 table had clk on E M4 (pre-GEOM-21).  Template clk -> N face M5 on the free M5 track
# nearest the face centre (>= 0.096 um from every N-face M5 pin): the one core clock entry, centred for TritonCTS.
import bisect
def clk_m5(pp, w=207.36, h=164.16):
    n = sorted(q["x"] for q in pp if q["layer"] == "M5" and q["y"] > h - 1)
    best = None
    for k in range(int(w / 0.048)):
        x = round(0.012 + 0.048 * k, 3)
        if not 5 < x < w - 5:
            continue
        i = bisect.bisect_left(n, x); d = min([abs(x - n[j]) for j in (i - 1, i) if 0 <= j < len(n)] + [99])
        if d >= 0.096 - 1e-9 and (best is None or abs(x - w / 2) < abs(best - w / 2)):
            best = x
    out = [dict(q) for q in pp]
    for q in out:
        if q["name"] == "clk":
            q.update(layer="M5", x=best, y=round(h - 0.24, 3))   # centre of the 0.048 x 0.48 GEOM-21 rect (contract LEF)
    return out, best
x1["pins"], cx = clk_m5(x1["pins"])
json.dump(x1, open("inputs/core_pins/ot_s81sl_xrt1_rf1.json", "w"), indent=1)
x3r = dict(x3, source=x3.get("source", "") + " | DIE-S81-51/RF-B 11-03: clk -> N M5 (GEOM-21), xrt template")
x3r["pins"], cx3 = clk_m5(x3["pins"]); assert cx3 == cx
json.dump(x3r, open("inputs/core_pins/ot_s81sl_xrt3_rf1.json", "w"), indent=1)
for t, v in plan["partition_types"].items():
    for h in v.get("hard_cores", []):
        if h["module"] == "ot_s81sl_xrt3":
            h.update(pins_file="inputs/core_pins/ot_s81sl_xrt3_rf1.json", rfb_note="RF-B 11-03 trial: xrt template")
json.dump(plan, open(dst, "w"), indent=1)
print("clk N M5 x", cx)
# GEOM-21 contract LEFs (only PIN clk, M5 0.048 x 0.48 at the N face): pins JSONs + plan hard_cores point at them.
LEF = {m: "physical/die_plan/s81/rf1/%s_rf1_contract.lef" % m for m in ("ot_s81sl_xrt1", "ot_s81sl_xrt3")}
for m in LEF:
    f = "inputs/core_pins/%s_rf1.json" % m
    d = json.load(open(f)); d["lef"] = LEF[m]; json.dump(d, open(f, "w"), indent=1)
for t, v in plan["partition_types"].items():
    for h in v.get("hard_cores", []):
        if h["module"] in LEF:
            h["lef"] = LEF[h["module"]]
json.dump(plan, open(dst, "w"), indent=1)
