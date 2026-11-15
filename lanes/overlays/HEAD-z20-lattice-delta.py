"""HEAD-99 delta for rp21z20 (HEAD-REMAP-1): G0C hard_cores lattice warnings.
Every hard core of hd_host_w / hd_serdes whose origin_um is off the 8.64-um lattice gets origin_um snapped to the nearest lattice point and the
difference moved into track_offset_um (schema: track_offset_um is added to origin_um at placement), so the placed position is unchanged.
usage: z20_lattice_delta.py PLAN_IN PLAN_OUT"""
import json, sys
G = 8.64
src, dst = sys.argv[1:3]
d = json.load(open(src)); n = 0
for tn in ("hd_host_w", "hd_serdes"):
    for h in d["partition_types"][tn]["hard_cores"]:
        o = h["origin_um"]; to = list(h.get("track_offset_um", [0.0, 0.0])); ch = False
        for i in (0, 1):
            k = round(o[i] / G); snap = round(k * G, 4)
            if abs(o[i] - snap) > 1e-6:
                to[i] = round(to[i] + (o[i] - snap), 4); o[i] = snap; ch = True
        if ch:
            h["track_offset_um"] = to; n += 1
            print(tn, h["inst"][-36:], "origin", o, "track_offset", to)
json.dump(d, open(dst, "w"), indent=1, ensure_ascii=False)
print("snapped", n, "cores")
