#!/usr/bin/env python3
"""DIE-HBM-5 die-local wrapper: die_trial.py kit --region-trees with SUB-PARTITION (hub W/E) clock regions.
REGION4 safe map = tok_l10_v1_c5 + NW/NE hub W/E split (hubsplit.py cut, region4/REGION4_SAFE_MAP.md).  die_trial's
--region-trees keys regions by partition; a hub is one partition, so its taps are assigned here by die x against the
planned cut: part_region[hub] = "RW|RE@x_cut".  Each half gets its own region root at its half-bbox centre and its own
equal-depth local tree (same FALLBACK-S81-2 construction, no pads/trims).  No shared-tool change: build_htree is
re-compiled from die_trial's own source with two textual edits (asserted).
usage: kit_hs.py TOOLS MAP_HUBSPLIT.json HUBSPLIT_REPORT.json OUT_MAP.json -- <die_trial kit args incl --region-trees OUT_MAP.json>"""
import json, sys
from pathlib import Path
tools, mhs, rep, omap = sys.argv[1:5]
assert sys.argv[5] == "--"
m = json.load(open(mhs))["part_region"]; r = json.load(open(rep))
pr = {k: v for k, v in m.items() if not k.endswith(("_hubW", "_hubE"))}
for hub in ("NW_hub", "NE_hub"):
    pr[hub] = f"{m[hub + 'W']}|{m[hub + 'E']}@{r[hub]['best']['x'] + r[hub]['x0']:.3f}"
    assert abs(r[hub]["best"]["x"] + r[hub]["x0"] - r[hub]["cut_abs_x"]) < 0.01
Path(omap).write_text(json.dumps(dict(part_region=pr, note="DIE-HBM-5 v1c5 + hub W/E split (kit_hs.py)"), sort_keys=True))
sys.path.insert(0, tools)
import die_trial as DT
import inspect
src = inspect.getsource(DT.build_htree)
a = "        rt[regions[t[0]]].append(t)\n"
b = ("        _rv = regions[t[0]]\n"
     "        if '@' in _rv:\n"
     "            _rr, _cx = _rv.split('@'); _rw, _re = _rr.split('|')\n"
     "            _rv = _rw if t[2] < float(_cx) else _re\n"
     "            _split[_rv] = (t[0], float(_cx), _rv == _rw)\n"
     "        rt[_rv].append(t)\n")
assert src.count(a) == 1
src = src.replace(a, b)
a2 = "    pseudo = ["
b2 = ("    for _rn, (_pn, _cx, _west) in _split.items():\n"
      "        _b = box[_rn]\n"
      "        box[_rn] = (_b[0], _b[1], _cx, _b[3]) if _west else (_cx, _b[1], _b[2], _b[3])\n"
      "    pseudo = [")
assert src.count(a2) == 1
src = src.replace(a2, b2)
a3 = "    rt = defaultdict(list)\n"
assert src.count(a3) == 1
src = src.replace(a3, a3 + "    _split = {}\n")
ns = {}
exec(compile(src, DT.__file__ + ":kit_hs", "exec"), DT.__dict__, ns)
DT.build_htree = ns["build_htree"]
import os
if os.environ.get("OT_HS_NO_STA") == "1":      # GRT-only kit: STA stand-in netlists are not a GRT input (they stall on the hubs)
    DT.standin_netlist = lambda P, tn: (f"module {P.types[tn]['module']} ();\nendmodule\n", 0)
    print("kit_hs: OT_HS_NO_STA=1 -> sta/parts are EMPTY stand-ins (GRT-only kit; not for die STA)", flush=True)
sys.argv = [DT.__file__] + sys.argv[6:]
DT.main()
