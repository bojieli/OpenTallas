#!/usr/bin/env python3
"""DIE-KV-69 11-04: kv3_io_cor_v1 one-block plan event, the GEOM-96 form that kv3_io_cor got in 32d3e2665d and this
type did not (kit @5: 4 grid taps, 23.5k sinks, tap insertion 626-715 ps, post-CTS hold -486.36).  Runs the GEOM-96
tools unchanged with TYPES set to this type; the tap sites come from geom96_1031/cover_taps.py (added_taps.json here).
col_v site is the @5 kit's AUTO-GEOM hot spot (1170, 192.5).
usage (repo root): event.py taps|start|raw PLAN_IN PLAN_OUT [RAWBR.json]|REPORT.json"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "geom96_1031"))
TN = "kv3_io_cor_v1"
step, a, b, c = sys.argv[1:5]
if step == "taps":
    import delta_geom96_taps as M
    M.ADDED = json.load(open(HERE / "added_taps.json"))
    sys.argv = ["x", a, b, c]
elif step == "start":
    import delta_geom96_start as M
    M.TYPES = (TN,)
    M.COLV_AT = {TN: (1170.0, 192.5)}
    sys.argv = ["x", a, b, c]
elif step == "raw":
    import delta_geom96_raw as M
    M.TYPES = (TN,)
    sys.argv = ["x", a, c, b]
M.main()
