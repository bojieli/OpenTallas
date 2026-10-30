#!/usr/bin/env python3
"""HBM-BIND-7 step 4: compare each coll cut core's module ports (compose spec) with the plan core kit pins (pins_file of
the plan hard core that the cut maps to).  Bus = name with [i] stripped; reports per core: missing in kit, extra in kit,
width differences.  Read-only.  usage: coll_kit_pin_diff.py PLAN.json COMPOSE.json MAP.json OUT.json"""
import collections, json, re, sys
from pathlib import Path
P, C, M, O = sys.argv[1:5]
plan = json.loads(Path(P).read_text()); spec = json.loads(Path(C).read_text()); mp = json.loads(Path(M).read_text())["parts"]
TYPE = {"NE_hub": "q_hub_ne", "NW_hub": "q_hub_nw"}
hard = {(p, h["inst"]): h for p, tn in TYPE.items() for h in plan["partition_types"][tn]["hard_cores"]}
base = Path(P).parent
out = {}
for c in spec["cores"]:
    if not c["inst"].startswith("hb_coll_N"):
        continue
    part, local = mp[c["inst"]]
    h = hard.get((part, local))
    if h is None:
        out[c["inst"]] = dict(error=f"plan hard core {local} not found"); continue
    pf = Path(h["pins_file"]); pf = pf if pf.is_absolute() else next((q for q in (base / pf, Path(P).parents[1] / pf) if q.exists()), pf)
    try:
        pins = json.loads(Path(pf).read_text())
    except Exception as e:
        out[c["inst"]] = dict(error=f"pins_file {pf}: {e}"); continue
    kit = collections.Counter(re.sub(r"\[\d+\]$", "", p[0] if isinstance(p, (list, tuple)) else p["name"]) for p in pins)
    cut = collections.Counter()
    for n, v in c["ports"].items():
        cut[re.sub(r"__b\d+$", "", n)] += len(v["bits"])
    out[c["inst"]] = dict(plan_local=local, plan_module=h["module"], cut_module=c["module"], kit_pins=sum(kit.values()),
                          cut_pins=sum(cut.values()), common_buses=len(set(kit) & set(cut)),
                          only_cut=sorted(f"{k}:{cut[k]}" for k in set(cut) - set(kit)),
                          only_kit=sorted(f"{k}:{kit[k]}" for k in set(kit) - set(cut)),
                          width_diff=sorted(f"{k}:cut{cut[k]}/kit{kit[k]}" for k in set(kit) & set(cut) if kit[k] != cut[k]))
Path(O).write_text(json.dumps(out, indent=1))
for k, v in out.items():
    if "error" in v: print(k, v["error"]); continue
    print(k, v["plan_module"], "->", v["cut_module"], "kit", v["kit_pins"], "cut", v["cut_pins"], "common", v["common_buses"],
          "only_cut", len(v["only_cut"]), "only_kit", len(v["only_kit"]), "width", len(v["width_diff"]))
