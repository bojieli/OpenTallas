#!/usr/bin/env python3
"""HBM-CORES-R7 vmdel_lane_n outline re-plan TRIAL (plan owner HBM-MU-QUAD-6 adopts or rejects; NOT a plan delta).
Content: 2 x ot_sram_1r1w_128x256_m1_r2c2 (94.824 x 41.064, pins M4 on W/E edges) + ~1045 um2 std cells; 929 pins
(W 564 M4, S 338 M5, E 27 M4).  Plan outline 257.04 x 108 (parent slot q_hub_nw/ne 2x2 block x 2540.16..3065.04,
y 2877.12..3097.44 above vms_glue, street 47.52) -> std-cell fill 0.06 of the free core.
Height 108 is PIN-LIMITED by the W face (564 M4 pins x 0.192 = 108.3 um), so only the width shrinks:
stack the two SRAMs vertically (abutted, row-grid pitch 41.31) at x0 = 30.24, y0 = 17.28 (4.32 lattice) ->
W std band 4.32..25.92 (face regs of the 564 W pins + SRAM W-edge pins), E channel 125.06..138.24 (SRAM E-edge pins),
S band 4.32..12.96 (338 S face regs).  Outline 142.56 x 108 (33 x 4.32): free core 5518 um2 -> fill ~0.19.
Trial pin table: W pins unchanged; S pins keep order, x rescaled into 9.0..137.976 and snapped to the M5 track
(0.024 + k*0.048), unique; E pins moved to x = 142.56.  Clock entry island moved into the W band centre
(12.96..21.6 x 47.52..56.16), pin (17.304, 51.84) on the M5 track.
usage: vmdel_trial.py VIEWS_U6b.json PLANDIR OUTDIR NETLIST"""
import json, re, sys, hashlib, copy
from pathlib import Path
views, plan, out, net = sys.argv[1:5]
out = Path(out); (out / "slices").mkdir(parents=True, exist_ok=True)
V = json.load(open(views)); v = [x for x in V["view_list"] if x["module"] == "ot_hbm_svc_vmdel_lane_n"][0]
pins = json.load(open(Path(plan) / v["pins_file"]))
face = lambda p: "S" if p["y"] < 1 else ("N" if p["y"] > 107 else ("W" if p["x"] < 1 else "E"))
for p in pins: p["_f"] = face(p)
W, H, OW = 142.56, 108.0, 257.04
S = sorted([p for p in pins if p["_f"] == "S"], key=lambda p: p["x"])
x0o, x1o = S[0]["x"], S[-1]["x"]; lo, hi = 9.0, W - 4.584
trk = lambda v_: round(0.024 + 0.048 * round((v_ - 0.024) / 0.048), 3)
used = set(); new = []
for p in pins:
    q = dict(p)
    if p["_f"] == "S":
        x = trk(lo + (p["x"] - x0o) / (x1o - x0o) * (hi - lo))
        while x in used: x = round(x + 0.048, 3)
        used.add(x); q["x"] = x
    elif p["_f"] == "E":
        q["x"] = W
    q.pop("_f"); new.append(q)
assert max(p["x"] for p in new) <= W and not any(p["_f"] == "N" for p in pins)
pf = out / "ot_hbm_svc_vmdel_lane_n__142.56x108__trialR7.json"
pf.write_text(json.dumps(new))
sha = hashlib.sha256(pf.read_bytes()).hexdigest()
nv = copy.deepcopy(v); nv.update(outline_um=[W, H], pins_file=str(pf.resolve()), pins_sha256=sha,
                                view=f"ot_hbm_svc_vmdel_lane_n@{sha[:12]}", note="HBM-CORES-R7 TRIAL outline 142.56x108 (not in plan)")
V2 = copy.deepcopy(V); V2["view_list"] = [nv]
(out / "views_vmdel_trial.json").write_text(json.dumps(V2, indent=1))
sl = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else None
isl = [12.96, 47.52, 21.6, 56.16]; ck = [17.304, 51.84]
sl["outline_um"] = [W, H]; sl["islands"][0].update(rect_um=isl, centre_um=ck, clock_pin=dict(layer="M5", xy_um=ck))
sl["note"] = "HBM-CORES-R7 vmdel TRIAL slice: outline 142.56x108, entry moved into the W band (plan entry was (129.6,51.8))"
(out / "slices" / "ot_hbm_svc_vmdel_lane_n.json").write_text(json.dumps(sl, indent=1))
names = sorted(set(re.findall(r"ot_sram_1r1w_128x256_m1_r2c2 \\(\S+)", open(net).read())))
names = [n[len("u_fcore."):] if n.startswith("u_fcore.") else n for n in names]
assert len(names) == 2, names
mp = [dict(k=n, macro="ot_sram_1r1w_128x256_m1_r2c2", origin_um=[30.24, round(17.28 + i * 41.31, 3)], orient="R0")
      for i, n in enumerate(sorted(names))]
(out / "vmdel_macro_placement.json").write_text(json.dumps(dict(schema="opentallas.macro_placement.v1",
    design="ot_hbm_svc_vmdel_lane_n", outline_um=[W, H], rule=__doc__.split("usage")[0].strip(), macro_placement=mp), indent=1))
free = (W - 8.64) * (H - 8.64) - 2 * 94.824 * 41.064
print("view", nv["view"], "S pins", len(S), "free core", round(free), "fill@1045", round(1045 / free, 3), mp)
