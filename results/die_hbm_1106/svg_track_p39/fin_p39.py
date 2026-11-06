#!/usr/bin/env python3
"""DIE-HBM-81 d44v part 39 packaging: event record, README line, SHA256SUMS.   fin_p39.py REPO"""
import gzip, hashlib, json, sys
from pathlib import Path
D = Path(sys.argv[1]) / "physical/die_plan/hbm/plan_of_record/d44v"
ev = {"schema": "opentallas.hbm_plan_event.part39", "by": "DIE-HBM-81 11-06 (G0C class C: hub svg pins off the M4 track, 96 errors)",
      "types": ["q_hub_nw", "q_hub_ne"], "cores": "u_svg_Q0/Q1 __b0 __b1 __o __t (MX)",
      "change": "track_offset_um y -0.024 -> 0.0 (core 24 nm up); the core's clock tap point y +0.024; pin tables, outlines, origins, Q2/Q3 unchanged",
      "why": "MX keeps pins at 0.024 mod 0.048 (outline heights are multiples of 0.048); with the -0.024 offset every pin was half an M4 pitch off the type track (offset 0.024, pitch 0.048)",
      "pin_cycles": "none", "replay": "results/die_hbm_1106/svg_track_p39/mk_p39.py + fin_p39.py"}
(D / "part39_event.json").write_text(json.dumps(ev, indent=1) + "\n")
rd = D / "README.md"
rd.write_text(rd.read_text().rstrip("\n") + "\n\nEvent part 39 (DIE-HBM-81 11-06, G0C class C): q_hub_nw/q_hub_ne u_svg_Q0/Q1 split cores (MX) track_offset y -0.024 -> 0.0 "
              "so their M4 pins sit on the type M4 track; clock tap points follow (+0.024); part39_event.json.\n")
S = D / "SHA256SUMS"
L = [l.split(None, 1) for l in S.read_text().splitlines() if l.strip()]
sha = lambda b: hashlib.sha256(b).hexdigest()
new = {"die_plan.json": sha(gzip.decompress((D / "die_plan.json.gz").read_bytes())), "part39_event.json": sha((D / "part39_event.json").read_bytes())}
ch = 0
for i, (a, n) in enumerate(L):
    if n in new and new[n] != a:
        L[i] = [new[n], n]; ch += 1
if "part39_event.json" not in {n for _, n in L}:
    L.append([new["part39_event.json"], "part39_event.json"])
S.write_text("".join(f"{a}  {n}\n" for a, n in L))
print("SHA256SUMS changed", ch)
