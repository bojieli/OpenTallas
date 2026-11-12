"""HBM-CORES-C 11-12 (DIE-HBM-101): ot_hgi_sfu_opsa_group0 placement lattice fix.

CLASS: plan delta d53a_layout_1111/deltas/opsa_b.py widened group0 to the left by DX = 135.0 um.  135.0 / 0.048 = 2812.5, so the
core origin x 945.0 is a half track pitch off the 0.048 lattice, and every core-frame M5 pin (x + 135, local phase 0.000) sits half a
pitch off the kit lattice (0.024 + 0.048 n): gen_core_kit_hbm.py stops with "2051 M4/M5 pins off the plan lattice" (all 2051 M5 pins,
none of the M4/M6/M7).  The absolute pin positions were right; the core frame was not.

FIX: move the origin onto the lattice (x 945.0 -> 944.976) and widen the outline by the same 0.024 (895.32 -> 895.344, right edge
1840.32 unchanged), and shift the core-frame table so the ABSOLUTE pin positions do not move: every M5 pin x + 0.024 (N/S faces), E-face
M4 pins x + 0.024 (they follow the right edge), W-face M4 pins keep x (they follow the left edge).
usage: opsa_g0_lattice.py PLAN_IN PLAN_OUT CORES_DIR   (writes PLAN_OUT and PLAN_OUT-dir/cores_d51/<new table>)"""
import json, os, sys
src, dst, cores = sys.argv[1:4]
D = json.load(open(src)); T = D["partition_types"]
OLD = "cores/ot_hgi_sfu_opsa_group0__895.32x270__d51opsaB.json"
NEW = "cores/ot_hgi_sfu_opsa_group0__895.344x270__d51opsaB_lat.json"
S = 0.024
pins = json.load(open(os.path.join(cores, os.path.basename(OLD))))
W0 = 895.32
out = []
for p in pins:
    q = dict(p)
    if p["layer"] == "M5": q["x"] = round(p["x"] + S, 4)
    elif p["layer"] == "M4" and p["x"] > W0 / 2: q["x"] = round(p["x"] + S, 4)
    out.append(q)
newp = os.path.join(os.path.dirname(os.path.abspath(dst)), "cores_d51", os.path.basename(NEW))
os.makedirs(os.path.dirname(newp), exist_ok=True); json.dump(out, open(newp, "w"))
n = 0
for tn, t in T.items():
    for h in t.get("hard_cores") or []:
        if h["module"] == "ot_hgi_sfu_opsa_group0":
            assert h["outline_um"] == [895.32, 270.0] and h["origin_um"] == [945.0, 1261.44] and h["pins_file"] == OLD, (tn, h)
            h["origin_um"] = [944.976, 1261.44]; h["outline_um"] = [895.344, 270.0]; h["pins_file"] = NEW; n += 1
assert n == 2, n
open(dst, "w").write(json.dumps(D, indent=1) + "\n")
print("instances", n, "pins file ->", newp, len(out))
