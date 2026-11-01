#!/usr/bin/env python3
"""DIE-KV-60/ioft 11-01 (AUTO-GEOM GRT FAIL kv3_io_ft / kv3_io_ft_v1, KIT-WAVE event28w_c): one-block plan event.

Measured (DIE-KV-60, CHECKED, intel1 die-kv-60/ioft/A): GRT congestion 391k at 2 % usage, ALL of it at x 0-100 /
y 500-700 um = the W-face ft2_i landing.  Cause: band ft2_i has no ring_place, so landing_placement.tcl packs ALL
11,851 ring cells (2,721 flops + read/write logic) FIRM in netlist order into the 51.84 x 87.34 um band; the
E-face twin band ft0_i (same frame, same 576-wide ring) has ring_place='ff' + fill_axis='x' (DIE-KV-32): only its
2,719 ring flops are FIRM, bit-major, and its 9,122 ring logic cells go to global placement -- that region has no
congestion in the same GRT.  DIE-HEAD-12 probe B (hd_tile) measured the same form change at -97 % overflow.

Fix (existing opt-in plan fields, no tool change): band ft2_i of kv3_io_ft and kv3_io_ft_v1 takes the form of its
twin band ft0_i.  Variant (sys.argv[3]):
  x  (V1)  ring_place='ff', fill_axis='x'  (exactly the ft0_i form)
  ff (V2)  ring_place='ff'                  (DIE-HEAD-13 row form, bit-major, auto spread to cland_ff_fill)
Measured (own place probes, wave synth+floorplan reused, geom_check.sh --all-kits, M2-M7): GRT overflow
206,673 (3 it) -> V1 0 / V2 0; V2 0 at 50 it.  V2 TAKEN: pin_reg_p90 101.7 -> 83.0 (V1 95.6), GRT wirelength
2.51 -> 1.64 m (V1 1.69 m); the +ff band runs as the pinslot form (2,664 of 2,719 ring flops beside their bit pin).
Band rects, pins, outlines, neighbours, RTL, clocks and every other field are unchanged (asserted).
usage: delta_ioft_ft2_ring.py PLAN_IN PLAN_OUT [ff|x]   (default ff = the plan of record)"""
import copy, json, sys

src, dst = sys.argv[1:3]
form = sys.argv[3] if len(sys.argv) > 3 else "ff"
assert form in ("x", "ff")
raw = json.load(open(src))
orig = copy.deepcopy(raw)
for tn in ("kv3_io_ft", "kv3_io_ft_v1"):
    bands = raw["partition_types"][tn]["clock"]["landing_contract"]["bands"]
    twin, b = bands["ft0_i"], bands["ft2_i"]
    assert twin.get("ring_place") == "ff" and twin.get("fill_axis") == "x", tn
    assert "ring_place" not in b and "fill_axis" not in b and "spread" not in b, tn
    assert b["ring_width"] == twin["ring_width"] and b["instance"] == "u_cland_ft2_i", tn
    b["ring_place"] = "ff"
    if form == "x":
        b["fill_axis"] = "x"
    b["resize_ioft_1101"] = ("DIE-KV-60/ioft 11-01: ring_place ff%s (only the ring flops FIRM, ring logic to GPL, as "
                             "twin band ft0_i); the all-cells FIRM ring jammed GRT (391k congestion at the W landing)"
                             % (" + fill_axis x" if form == "x" else ""))
# nothing else changed
chk = copy.deepcopy(raw)
for tn in ("kv3_io_ft", "kv3_io_ft_v1"):
    b = chk["partition_types"][tn]["clock"]["landing_contract"]["bands"]["ft2_i"]
    for k in ("ring_place", "fill_axis", "resize_ioft_1101"):
        b.pop(k, None)
assert chk == orig
open(dst, "w").write(json.dumps(raw, indent=1) + "\n")
print(f"kv3_io_ft, kv3_io_ft_v1: band ft2_i ring_place=ff{' fill_axis=x' if form == 'x' else ''}")
