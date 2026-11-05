"""DIE-QC-74 11-05 band class (plan delta, fix-only): 3 su_l1 types never took the ring_ff band resize.

kit-wave place FAIL 'OT_CLAND no legal ... u_cland_cws0_i (ring:cws0_i): 11695 cells reserve 3802.9 um2 > band upper
bound 2930.0 um2 (ratio 1.30), checked before placement' on sle_su_l1__cl5ea486db, slw_su_l1__clcc9d0155.  The ring is the
same as su_l0 cws3_i (W 516, ring 576), which has resized_from_um and placed.  Of 1177 QC ring bands, 19 are below
ring_ff_reserve_um2, all in these 3 types.  No window grow reaches this, the ring is what does not fit.  The single-rect
resize_undersized_bands fails on rsn_i ('no macro-free ... required depth 51.84 um'), so those bands take the
multi-rect form of DIE-S81-47 (fill_failed_bands, reset sites as obstacles) at the ring_ff reserve.  Other types, bands
and keys stay byte-identical.

usage: delta_sul1_band.py PLAN SIDECAR OUT REPORT
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "..", "tools", "die_plan"))
import clock_landing_plan as CP  # noqa: E402

TYPES = ["sle_su_l1__cl5ea486db", "slw_su_l1__clcc9d0155", "slw_su_l1__cla2a78701"]


def apply(plan, sidecar, types=TYPES):
    p = json.loads(json.dumps(plan))
    for tn in types:
        for bus, b in p["partition_types"][tn]["clock"]["landing_contract"]["bands"].items():
            if bus.startswith("monitor_") or not b.get("rect_um"):
                continue
            x0, y0, x1, y1 = b["rect_um"]
            if (x1 - x0) * (y1 - y0) + 1e-6 < CP.ring_ff_reserve_um2(b["width"]):
                b["placement"] = "FAIL"
    return CP.fill_failed_bands(p, sidecar, types, band_reserve="ring_ff")


if __name__ == "__main__":
    plan_in, side, out, rep = sys.argv[1:5]
    new, report = apply(json.load(open(plan_in)), json.load(open(side)))
    json.dump(report, open(rep, "w"), indent=1)
    open(out, "w").write(json.dumps(new) + "\n")
