#!/usr/bin/env python3
"""DIE-HBM-81 d44v part 39: hub SVGR split cores on the M4 track (G0C class C, hard_cores 96).

q_hub_nw / q_hub_ne u_svg_Q0 / u_svg_Q1 {__b0,__b1,__o,__t} are MX with track_offset y -0.024.  Their pin tables sit
on M4 track centres (y = 0.024 mod 0.048) and every outline height is a multiple of 0.048, so after MX the pins stay at
0.024 mod 0.048 and the -0.024 offset puts them half a pitch off the type's M4 track (offset 0.024, pitch 0.048):
2251 pins per core off track (check.py hard_cores).  Fix: y offset -0.024 -> 0.0 (24 nm up), the matching clock tap
point moves with it.  Q2/Q3 (MY, offsets -0.048 / 0.0) are already on track and stay.  Nothing else changes.
    mk_p39.py D44V_DIR"""
import gzip, json, re, sys
from pathlib import Path
D = Path(sys.argv[1])
P = json.loads(gzip.decompress((D / "die_plan.json.gz").read_bytes()))
PAT = re.compile(r"^u_svg_Q[01]__(b0|b1|o|t)$")
log = []
for tn in ("q_hub_nw", "q_hub_ne"):
    T = P["partition_types"][tn]
    for h in T["hard_cores"]:
        if not PAT.match(h["inst"]):
            continue
        assert h.get("orient") == "MX" and h["track_offset_um"][1] == -0.024, (tn, h["inst"], h.get("orient"), h["track_offset_um"])
        assert round(h["outline_um"][1] / 0.048, 6) == int(round(h["outline_um"][1] / 0.048)), h["outline_um"]
        h["track_offset_um"] = [h["track_offset_um"][0], 0.0]
        h["note"] = (h.get("note", "") + " | DIE-HBM-81 d44v part 39: MX track_offset y -0.024 -> 0.0 (pins onto the M4 track)").lstrip(" |")
        nt = 0
        for tp in T["clock"]["taps"]:
            if tp.get("name") == h["inst"]:
                tp["xy"] = [tp["xy"][0], round(tp["xy"][1] + 0.024, 4)]
                nt += 1
        log.append((tn, h["inst"], nt))
assert len(log) == 16, log
b = (json.dumps(P) + "\n").encode()
with open(D / "die_plan.json.gz", "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
    g.write(b)
for x in log:
    print("P39", *x)
