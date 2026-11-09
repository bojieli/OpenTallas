#!/usr/bin/env python3
"""merge per-type ring_band_spread outputs into one plan (each type's object from its own run; base bytes elsewhere)"""
import json, sys, glob, os
sys.path.insert(0, "tools/die_plan")
import ring_band_spread as R
import schema as S
from pathlib import Path
base, pardir, out, rep_out = sys.argv[1:5]
text = open(base).read(); plan = json.loads(text); changed = []; rows = []
for rp in sorted(glob.glob(pardir + "/*.rep.json")):
    tn = os.path.basename(rp)[:-9]
    r = json.load(open(rp)); rows += r["rows"]
    if tn in r["types_changed"]:
        plan["partition_types"][tn] = json.load(open(pardir + f"/{tn}.plan.json"))["partition_types"][tn]
        changed.append(tn)
o = R.splice(text, plan, changed)
assert json.loads(o) == plan
S.Plan(json.loads(o), Path(base).resolve())
open(out, "w").write(o)
over = [x for x in rows if (x.get("hop_um") or 0) > 405]
json.dump(dict(types_changed=changed, bands_resized=sum("new_um" in x for x in rows),
               bands_kept=[x for x in rows if "error" in x or "skipped" in x], hop_over_405=over, rows=rows), open(rep_out, "w"), indent=1)
print("types", len(changed), "bands", sum("new_um" in x for x in rows), "kept", len([x for x in rows if "error" in x]), "over405", len(over))
