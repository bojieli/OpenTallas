#!/usr/bin/env python3
"""PATH-S81-PD6 cut evidence step 1: the 13 G0 cut errors -> (orient, at_um, part, segment lo/hi um) from the plan."""
import gzip, json, re, sys
from pathlib import Path
wt, plan, g0, out = sys.argv[1:5]
sys.path.insert(0, str(Path(wt) / "tools/die_plan"))
import schema as S
P = S.Plan(S.load(plan))
R = json.load(gzip.open(g0)) if g0.endswith(".gz") else json.load(open(g0))
rx = re.compile(r"(vertical|horizontal) cut at ([\d.]+): (\S+) segment carries (\d+) bits on (\d+) tracks = ([\d.]+)")
cuts = []
for f in R["findings"]:
    if f["level"] != "ERROR" or f["check"] != "cuts":
        continue
    m = rx.search(f["msg"])
    o, c, pn, bits, tr, ratio = m.groups()
    r = P.rect(pn)
    lo, hi = (r[1], r[3]) if o == "vertical" else (r[0], r[2])
    cuts.append(dict(orient=o, at_um=float(c), part=pn, bits=int(bits), g0_tracks=int(tr), g0_ratio=float(ratio),
                     seg_lo_um=lo, seg_hi_um=hi, part_rect_um=list(r)))
json.dump(cuts, open(out, "w"), indent=1)
for c in cuts:
    print(c["orient"], c["at_um"], c["part"], c["g0_ratio"], c["seg_lo_um"], c["seg_hi_um"])
