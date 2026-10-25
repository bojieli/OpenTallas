#!/usr/bin/env python3
"""PATH-S81 10-25: s_3S_C (type dsdv_slice_iq_C__t1) hub xrt master xrt1 -> xrt3 (actual source).  Idempotent.

As built (die top die_b178.v): u_s_3S = ot_s81sl_slice_iq_w3 #(.HB(1)), so u_s_3S.u_sl.g_c3.u_xr = ot_s81sl_xrt3 --
the plan carried ot_s81sl_xrt1 (gen_plan_v4 keyed the xrt on a 'c3x' master-name substring; fixed with slice_xrt()
in the same commit).  Codex S81-bind 14:13 EMIT finding; no xrt1->xrt3 aliasing in the binder.
The iq_C u_c.u_xr entry takes the c3x_C xrt3 view as-is (lef, pins_file, outline 207.36 x 164.16, obs_max M6, MX,
track offset): one xrt3 type for both HB=1 hubs.  Placement: inside the old xrt1 footprint, right-aligned to it
(17.28 um W of u_c.u_xf, as before) and top-aligned with xf exactly as c3x_C places it (y 1019.52) -> no new overlap.
usage: delta_xrt3_iq_1025.py PLAN.json
"""
import json
import sys

T, REF, INST = "dsdv_slice_iq_C__t1", "dsdv_slice_c3x_C__t1", "u_c.u_xr"
OLD = dict(module="ot_s81sl_xrt1", origin_um=[388.8, 794.88], outline_um=[311.04, 395.28])
COPY = ("module", "lef", "outline_um", "orient", "track_offset_um", "pins_file", "obs_max")


def main():
    pf = sys.argv[1]
    plan = json.load(open(pf))
    ref = next(c for c in plan["partition_types"][REF]["hard_cores"] if c["inst"] == INST)
    assert ref["module"] == "ot_s81sl_xrt3", ref
    c = next(c for c in plan["partition_types"][T]["hard_cores"] if c["inst"] == INST)
    if c["module"] == "ot_s81sl_xrt3":
        print("delta_xrt3_iq: already applied")
        return
    for k, v in OLD.items():
        assert c[k] == v, (k, c[k])
    for k in COPY:
        c[k] = ref[k]
    ox, oy = OLD["origin_um"]
    ow, oh = OLD["outline_um"]
    nw, nh = c["outline_um"]
    c["origin_um"] = [round(ox + ow - nw, 4), round(ref["origin_um"][1], 4)]
    assert ox <= c["origin_um"][0] and c["origin_um"][1] + nh <= oy + oh, c["origin_um"]
    t = plan["partition_types"][T]
    t["note"] = t.get("note", "") + ("; PATH-S81 10-25: u_c.u_xr = ot_s81sl_xrt3 (actual HB=1 source, die_b178 u_s_3S "
                                     "#(.HB(1))), c3x_C xrt3 view, origin %s" % c["origin_um"])
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "results" / "s81_plan2_1025"))
    import pdump                     # the plan's own layout (round-trips die_plan.json byte for byte)
    open(pf, "w").write(pdump.dumps(plan))
    print("delta_xrt3_iq: %s %s -> xrt3 at %s" % (T, INST, c["origin_um"]))


if __name__ == "__main__":
    main()
