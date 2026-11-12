#!/usr/bin/env python3
"""encode_lat.py IN OUT [TYPE] : geometry-identical lattice encoding of hard cores (origin floored to the 8.64 lattice,
the remainder in track_offset_um).  The placed box origin + track_offset is unchanged to 1e-3 um, so nothing a reset
or street pass decided can move.  Cores already on the lattice are left as they are."""
import json, sys
LAT = 8.64
P = json.load(open(sys.argv[1])); tn = sys.argv[3] if len(sys.argv) > 3 else "hd_lep0N"; n = 0
for h in P["partition_types"][tn]["hard_cores"]:
    ox, oy = h["origin_um"]; dx, dy = h.get("track_offset_um", [0, 0])
    if abs(ox / LAT - round(ox / LAT)) < 1e-6 and abs(oy / LAT - round(oy / LAT)) < 1e-6: continue
    ax, ay = round(ox + dx, 3), round(oy + dy, 3)
    lx, ly = round((ax + 1e-6) // LAT * LAT, 3), round((ay + 1e-6) // LAT * LAT, 3)
    h["origin_um"] = [lx, ly]; h["track_offset_um"] = [round(ax - lx, 3), round(ay - ly, 3)]; n += 1
json.dump(P, open(sys.argv[2], "w"), indent=1); print("encoded", n)
