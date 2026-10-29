"""DIE-QC-22: why su_c early-tap core views do not match. usage: viewprobe.py TOOLS PLAN MODULE=DIR..."""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, sys.argv[1]); import die_sta_related as D, schema as S
plan_path = sys.argv[2]; plan = S.load(plan_path)
views = dict(a.split("=", 1) for a in sys.argv[3:])
P = S.Plan(plan)
seen = collections.Counter()
for n, prt in P.parts.items():
    t = P.types[prt["type"]]
    if (t.get("clock", {}) or {}).get("core_taps") != "early": continue
    for h in t.get("hard_cores", []) or []:
        seen[(h["module"], h.get("pins_file"), tuple(h.get("outline_um") or ()))] += 1
plan_pins = sorted({k[1] for k in seen if k[1]})
for (m, pf, ol), c in sorted(seen.items(), key=str):
    r = None
    if m in views:
        cm = D.core_view_model(m, views[m], "TT", 6.0, 0.0)
        r = D.pins_relation(cm["meta"], pf, Path(plan_path).resolve().parent, list(ol), plan_pins)
        r = (r, cm["meta"].get("pins_file"), cm["meta"].get("pins_sha256"))
    print(c, m, pf, ol, "->", r)
