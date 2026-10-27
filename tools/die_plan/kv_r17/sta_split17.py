#!/usr/bin/env python3
"""CLOCK-KV-R17 classification wrapper: runs die_sta_related.main with the pair set split by band involvement
(SPLIT=mesh: drop every pair with a leaf-fed band tap; SPLIT=band: keep only pairs with one).  INFO only."""
import json, os, sys
from pathlib import Path
import die_sta_related as R
band = {t["port"] for t in json.loads((Path(sys.argv[1]) / "mesh.json").read_text())["taps"] if t.get("mesh_in")}
mode = os.environ["SPLIT"]
orig = R.build_pairs
def bp(plan, taps):
    pairs, cov = orig(plan, taps)
    keep = (lambda a, b: a not in band and b not in band) if mode == "mesh" else (lambda a, b: a in band or b in band)
    return {k: [p for p in v if keep(p[0], p[1])] for k, v in pairs.items()}, cov
R.build_pairs = bp
R.nearest_pairs = lambda *a, **k: {}
sys.exit(R.main())
