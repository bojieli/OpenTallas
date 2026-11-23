#!/usr/bin/env python3
"""FABLE-UNC-QC: tap-offset coverage census. For every density-tap type: kit clock ports (clk, clk_t1..clk_t<base-1>, added taps)
vs plan clock.tap_offset.per_port_ps[type]. A port missing from a listed type's table is charged the full span [-W, 0] in the kit SDC.
usage (cwd = launch tree): python3 -I -B census.py PLAN OUT.tsv"""
import sys, json, collections
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import schema, taps as TP, gen_phys as GP
plan = sys.argv[1]; raw = json.load(open(plan)); P = schema.Plan(raw, Path(plan))
off = ((raw["clock"].get("tap_offset") or {}).get("per_port_ps") or {})
parts = collections.Counter(q["type"] for q in raw["partitions"])
rows = []
for tn, ty in raw["partition_types"].items():
    ck = ty.get("clock") or {}
    if ck.get("tap_mode") != "density": continue
    try: nb = len(TP._density_base(P, tn))
    except Exception as e:
        rows.append((tn, "ERR", str(e)[:80])); continue
    added = [a["name"] for a in ck.get("added_taps") or []]
    ports = ["clk"] + [f"clk_t{i}" for i in range(1, nb)] + added
    tab = off.get(tn) or {}
    miss = [p for p in ports if p not in tab]
    stale = [p for p in tab if p not in ports and not p.startswith("clk_c")]
    try: W = GP.tap_window_ps(P, tn)
    except Exception as e: W = "ERR"
    tols = sorted({v["tol"] for v in tab.values()}) if tab else []
    rows.append((tn, parts[tn], nb, len(added), len(tab), len(miss), len(stale), W, tols[:3], miss[:3] + (["..", miss[-1]] if len(miss) > 3 else [])))
with open(sys.argv[2], "w") as f:
    f.write("type\tinstances\tdensity_base\tadded\toffset_rows\tports_missing\tstale_rows\twindow_ps\ttol\tmissing_sample\n")
    for r in sorted(rows, key=lambda r: (-(r[5] if isinstance(r[5], int) else 9999), r[0])):
        f.write("\t".join(str(x) for x in r) + "\n")
bad = [r for r in rows if isinstance(r[5], int) and r[5] and r[4]]
print("TAPOFF census types", len(rows), "listed types with missing ports", len(bad), "ports", sum(r[5] for r in bad), "instances", sum(r[1] for r in bad))
print("unlisted types (flat window)", sum(1 for r in rows if isinstance(r[4], int) and not r[4]))
