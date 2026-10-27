#!/usr/bin/env python3
"""HBM-CORES-R7: COORD 05:43 SHARED RULE ext: clock port centre ON the M5 track (x = 0.024 + k*0.048, make_tracks.tcl)
AND >= 0.048 x 0.48.  Main master_slice.py (pre S81-CORE-LAT-R16) already writes 0.048x0.48 but snaps the centre to the
0.048 grid = 0.024 off track (e.g. pslice 470.904 -> 470.880).  This re-snaps the single master-slice clock line of the
kit io.tcl (+ master_slice.json clock_pin) to the nearest track; idempotent; writes clkpin_fix.json.  usage: KIT..."""
import json, re, sys
from pathlib import Path
P, O = 0.048, 0.024
snap = lambda v: round(O + P * round((v - O) / P), 3)
for kd in map(Path, sys.argv[1:]):
    ms = json.loads((kd / "master_slice.json").read_text())
    port = ms["core_clock_port"]
    hits = []
    for f in sorted(kd.glob("*.tcl")):
        t = f.read_text(); n = [0]; was = []
        def rep(m):
            x, y = float(m.group(2)), float(m.group(3)); was.append((x, y)); n[0] += 1
            return f"{m.group(1)}-location {{{snap(x):.4f} {y:.4f}}} -pin_size {{0.048 0.48}}{m.group(4)}"
        t2 = re.sub(r"(\{" + re.escape(port) + r"\} -layer M5 )-location \{([\d.]+) ([\d.]+)\} -pin_size \{0\.0(?:32|48) 0\.(?:192|48)\}(\s+;# master-plan slice)", rep, t)
        if n[0]:
            f.write_text(t2); hits.append((f.name, was))
    if len(hits) != 1 or len(hits[0][1]) != 1:
        raise SystemExit(f"{kd.name}: expected exactly one clock line, got {hits}")
    x0, y0 = hits[0][1][0]; x1 = snap(x0)
    for i in ms["islands"]:
        if i.get("clock_pin"):
            i["clock_pin"]["xy_um"] = [x1, y0]; i["centre_um"] = [x1, y0]
    (kd / "master_slice.json").write_text(json.dumps(ms, indent=1) + "\n")
    (kd / "clkpin_fix.json").write_text(json.dumps(dict(port=port, was=[x0, y0], now=[x1, y0], pin_size=[0.048, 0.48],
        file=hits[0][0], rule="COORD 10-27 05:43: clock port centre on M5 track (0.024+k*0.048) and >=0.048x0.48"), indent=1) + "\n")
    print(kd.name, port, [x0, y0], "->", [x1, y0])
