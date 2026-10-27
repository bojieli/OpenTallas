#!/usr/bin/env python3
"""HBM-KITS-1 (COORD rule 10-27): centre-entry clock port >= 0.048 x 0.48 um ON its M5 routing track
(0.032x0.192 caused DRT-0255). Interim until S81-CORE-LAT-R15 puts it in the shared kit_cts_hook.
M5 is vertical: x snapped to the track 0.024 + k*0.048 (collar R5 43.2 -> 43.224 precedent). Edits the master-slice
clock line in the kit Tcl + master_slice.json island/clock_pin; writes clkpin_fix.json.  usage: clkpin_fix.py KIT..."""
import json, re, sys
from pathlib import Path
P, O = 0.048, 0.024
def snap(v): return round(O + P * round((v - O) / P), 3)
for kd in map(Path, sys.argv[1:]):
    ms = json.loads((kd / "master_slice.json").read_text())
    isl = [i for i in ms["islands"] if i.get("clock_pin")][0]
    x0, y0 = isl["clock_pin"]["xy_um"]; x1 = snap(x0)
    port = ms["core_clock_port"]; hits = []
    for f in sorted(kd.glob("*.tcl")):
        t = f.read_text(); n = [0]
        def rep(m):
            n[0] += 1
            return f"{m.group(1)}-location {{{x1:.4f} {y0:.4f}}} -pin_size {{0.048 0.48}}{m.group(2)}"
        t2 = re.sub(r"(\{" + re.escape(port) + r"\} -layer M5 )-location \{[\d.]+ [\d.]+\} -pin_size \{0\.032 0\.192\}(\s+;# master-plan slice)", rep, t)
        if n[0]: f.write_text(t2); hits.append(f"{f.name}:{n[0]}")
    if len(hits) != 1: raise SystemExit(f"{kd.name}: expected exactly one clock line, got {hits}")
    isl["clock_pin"]["xy_um"] = [x1, y0]; isl["centre_um"] = [x1, y0]
    (kd / "master_slice.json").write_text(json.dumps(ms, indent=1) + "\n")
    (kd / "clkpin_fix.json").write_text(json.dumps(dict(port=port, was=[x0, y0], now=[x1, y0], pin_size=[0.048, 0.48],
        files=hits, rule="COORD 10-27 HBM-KITS-1: >=0.048x0.48 on track"), indent=1) + "\n")
    print(kd.name, port, [x0, y0], "->", [x1, y0], hits)
