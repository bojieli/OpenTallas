#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-5 IR summary: per kit VDD drop / VSS bounce over load-block terminals.
int kits: 'interior' = >= EDGE um from every (open) window edge. edgeW kits: x=0 is the real die edge (bumps stop at the
die channel), the other 3 sides are open: 'edge' = >= EDGE um from y0/y1/x1, split into die-edge band x < EDGE and the rest."""
import csv, json, sys
from pathlib import Path
E = 450.0
def load(p, vdd):
    out = []
    for r in csv.DictReader(open(p)):
        out.append((float(r["X location"]), float(r["Y location"]), (0.7 - float(r["Voltage"]) if vdd else float(r["Voltage"])) * 1e3))
    return out
res = {}
for k in sys.argv[1:]:
    k = Path(k); m = json.loads((k / "irwin.json").read_text())
    x0, y0, x1, y1 = m["window_um"]; W, H = x1 - x0, y1 - y0
    row = dict(window=m["window"], pad_um=m.get("bump_pad_um"), grid=m["grid"], power_w=m["power_w"], tracks=m.get("tracks"))
    log = (k / "psm" / "psm.log").read_text() if (k / "psm" / "psm.log").exists() else ""
    row["bumps_line"] = next((l for l in log.splitlines() if l.startswith("OT_BUMPS")), None)
    row["pg_check"] = [l for l in log.splitlines() if l.startswith("OT_PG_CHECK")]
    for net in ("VDD", "VSS"):
        p = k / "psm" / f"ir_{net}.csv"
        if not p.exists(): row[net] = None; continue
        g = load(p, net == "VDD")
        d = dict(all=max(v for *_, v in g))
        if "edgeW" in m["window"]:
            sel = [(x, y, v) for x, y, v in g if min(y, H - y, W - x) >= E]
            d["die_edge_band"] = max(v for x, y, v in sel if x < E)
            d["inner"] = max(v for x, y, v in sel if x >= E)
        else:
            d["interior"] = max(v for x, y, v in g if min(x, y, W - x, H - y) >= E)
            d["interior_avg"] = sum(v for x, y, v in g if min(x, y, W - x, H - y) >= E) / sum(1 for x, y, v in g if min(x, y, W - x, H - y) >= E)
        row[net] = {a: round(b, 2) for a, b in d.items()}
    res[k.name] = row
    f = lambda n, key: (row[n] or {}).get(key)
    keys = ("die_edge_band", "inner") if "edgeW" in m["window"] else ("interior",)
    print(k.name, " | ".join(f"{key}: VDD {f('VDD', key)} VSS {f('VSS', key)} sum {round((f('VDD', key) or 0) + (f('VSS', key) or 0), 2)}" for key in keys), "|", row["bumps_line"])
print(json.dumps(res, indent=1), file=open("/dev/stderr", "w") if False else sys.stderr)
