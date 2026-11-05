"""DIE-QC-77 11-05 band class (plan delta, fix-only): every QC ring band takes ring_place=ff.

Measured on sle_fe_v3 (ring_place=ff in the kit's landing_placement only, same floorplan, same outline, same rects):
GRT overflow 0 at extra iteration 7, 18.5 min. Same-iteration QC rows with all-cell ring FIRM read 211823-606926 at i5 and
plateau above 50000 after hours. Form is the existing opt-in of DIE-HEAD-13 (flops FIRM bit-major, ring logic to global
placement), used on S81, hd_tile and kv3_hub_Ei. Band rects, outlines, pins, RTL and ring contents are unchanged; only the
ring_place field moves. monitor_ bands and bands without a rect stay as they are, as in the pilot.

usage: delta_ring_ff.py PLAN OUT REPORT
"""
import json, sys


def apply(plan):
    p = json.loads(json.dumps(plan))
    rep = {}
    for tn, t in p["partition_types"].items():
        bands = ((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
        moved = []
        for bus, b in bands.items():
            if bus.startswith("monitor_") or not b.get("rect_um") or b.get("ring_place") == "ff":
                continue
            b["ring_place"] = "ff"
            moved.append(bus)
        if moved:
            rep[tn] = moved
    return p, rep


if __name__ == "__main__":
    plan_in, out, rp = sys.argv[1:4]
    new, report = apply(json.load(open(plan_in)))
    json.dump({"types": len(report), "bands": sum(map(len, report.values())), "moved": report}, open(rp, "w"), indent=1)
    open(out, "w").write(json.dumps(new) + "\n")
