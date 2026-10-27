"""Independent identity check (NUMBER-CHECK aid): from r13_top_sites.json cell origins, invert each partition's
orientation to the TYPE frame and compare per-instance cell sets within each type. Channel kinds excluded (die-level)."""
import json, sys
from collections import defaultdict
plan = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2]))
parts = {p["name"]: p for p in plan["partitions"]}
CW_ROW = 0.27
ORIENT = "--orient" in sys.argv
inst = defaultdict(lambda: defaultdict(list))
chan = 0
for name, c in S["cell_sites"].items():
    if c["kind"].startswith("chan"):
        chan += 1; continue
    p = parts[c["part"]]; (x0, y0), (w, h) = p["origin_um"], plan["partition_types"][p["type"]]["outline_um"]
    o = p.get("orient", "R0")
    x, y = c["origin_um"]
    tx = (x0 + w - x - c["w"]) if o in ("MY", "R180") else x - x0
    ty = (y0 + h - y - CW_ROW) if o in ("MX", "R180") else y - y0
    co = c.get("orient", "R0")
    if o in ("MY", "R180"):          # die-frame cell orient -> type frame (x mirror flips R0<->MY)
        co = {"R0": "MY", "MY": "R0"}.get(co, co)
    inst[p["type"]][c["part"]].append((round(tx, 3), round(ty, 3), c["master"], co if ORIENT else ""))
bad = []
for t, d in inst.items():
    sets = {n: tuple(sorted(v)) for n, v in d.items()}
    ref = next(iter(sets.values()))
    nd = sum(1 for v in sets.values() if v != ref)
    alln = [n for n in parts if parts[n]["type"] == t]
    missing = [n for n in alln if n not in sets]
    if nd or missing:
        bad.append((t, nd, len(missing), len(alln)))
print(json.dumps(dict(types=len(inst), hosted_instances=sum(len(d) for d in inst.values()), chan_cells=chan,
                      types_not_identical=bad, verdict="IDENTICAL" if not bad else "DIFF")))
