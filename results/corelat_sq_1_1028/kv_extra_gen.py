#!/usr/bin/env python3
"""CORELAT-SQ-1 KV: the KV plan (hm_r26q9b) binds NO lef/lib for any hard core -> numbers from the repo view the main
tool would pick (cores.find_views default: shortest ref_tile dir name; identity = module name only, UNCHECKED):
core.json clock_latency_measured (routed register census) > insertion.json boundary > lib ETM clock_tree_path range."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import cores as C
tab = json.load(open(sys.argv[1])); out = {}
def etm(fp):
    t = open(fp).read(); tu = 1000.0 if re.search(r"time_unit\s*:\s*\"1ns\"", t) else 1.0; o = {}
    for k in ("max_clock_tree_path", "min_clock_tree_path"):
        v = []
        for m in re.finditer(r"timing_type\s*:\s*\"?%s\"?\s*;(.*?)\}\s*\}" % k, t, re.S):
            v += [float(x) for y in re.findall(r"values\s*\(\s*\"([^\"]+)\"", m.group(1)) for x in re.findall(r"[-+]?\d+(?:\.\d+)?", y)]
        if v: o[k] = (min(v) * tu, max(v) * tu)
    return o
for r in tab["rows"]:
    mod = r["module"]; lef, tt, ff = C.find_views("physical/ref_tile", mod)
    if not tt:
        continue
    d = Path(tt).parent; rel = str(d.relative_to(Path.cwd().resolve())) if str(d).startswith(str(Path.cwd().resolve())) else str(d)
    cj = d / f"{mod}.core.json"; ins = d / "insertion.json"
    if cj.is_file() and (json.load(open(cj)).get("clock_latency_measured") or {}).get("tt"):
        m = json.load(open(cj))["clock_latency_measured"]
        out[mod] = dict(label=f"parent_budget register census {rel}/{mod}.core.json clock_latency_measured (routed; all registers, n={m['tt']['n']})",
                        tt={k: m["tt"][k] for k in ("mean", "min", "max")}, ff={k: m["ff"][k] for k in ("mean", "min", "max")},
                        checked="CHECKED read; view identity UNCHECKED (plan binds no view; module-name pick)")
    elif ins.is_file() and (json.load(open(ins)).get("tt") or {}).get("boundary", {}).get("n"):
        j = json.load(open(ins))
        out[mod] = dict(label=f"parent_budget pin_register_mean {rel}/insertion.json boundary (routed {j.get('parasitics')})",
                        tt={k: j["tt"]["boundary"][k] for k in ("mean", "min", "max")}, ff={k: j["ff"]["boundary"][k] for k in ("mean", "min", "max")},
                        checked="CHECKED read; view identity UNCHECKED (plan binds no view; module-name pick)")
    else:
        e = etm(tt); f = etm(ff) if ff else {}
        if "max_clock_tree_path" not in e: continue
        lo, hi = e.get("min_clock_tree_path", e["max_clock_tree_path"])[0], e["max_clock_tree_path"][1]
        flo, fhi = (f.get("min_clock_tree_path", f.get("max_clock_tree_path", (None,)))[0], f["max_clock_tree_path"][1]) if f.get("max_clock_tree_path") else (lo * .81, hi * .81)
        out[mod] = dict(label=f"parent_budget lib_etm_range {rel} (ETM min..max clock_tree_path, mean = midpoint; NOT a register census)",
                        tt=dict(mean=round((lo + hi) / 2, 1), min=round(lo, 1), max=round(hi, 1)),
                        ff=dict(mean=round((flo + fhi) / 2, 1), min=round(flo, 1), max=round(fhi, 1)),
                        checked="UNCHECKED (ETM range; view identity by module name)")
json.dump(out, open(sys.argv[2], "w"), indent=1); print(len(out), "KV modules with numbers")
