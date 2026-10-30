#!/usr/bin/env python3
"""DIE-HBM-29 (COORD 21:25 ruling 4): fold ot_hgi_sm_xload_xq_pegress (u_xq_Q_p0_eg / u_xq_Q_p1_eg) into the hub
partition as soft logic (die-local plan delta).  Removes the 2 hard cores per hub type, their plan clock taps,
clock_entries, core_conns and the internal stations that end on them; keeps the contents entry (status reuse, cells)
so the hub glue carries the logic; bind map: the xq leaves map to the hub partition (string form = soft leaf).
usage: xq_fold.py PLAN_DIR(in place) SRC_MAP OUT_MAP
"""
import json, sys
from pathlib import Path

D, SMAP, OMAP = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
P = json.loads((D / "die_plan.json").read_text())
CC = json.loads((D / "core_conns.json").read_text())
CE = json.loads((D / "clock_entries.json").read_text())
X = ("u_xq_Q_p0_eg", "u_xq_Q_p1_eg")
rep = {"event": "DIE-HBM-29 xq_pegress hub fold", "types": {}}

def ends(e):
    return {(e.get(k) or "").split(".")[0] for k in ("launch", "capture")} | \
           {s.split(".")[0] for s in (e.get("conn") or "").split("|")}

for t in ("q_hub_nw", "q_hub_ne"):
    v = P["partition_types"][t]
    r = {}
    hcs = [h for h in v["hard_cores"] if h["inst"] in X]
    r["removed_cores"] = [(h["inst"], h["module"], h["outline_um"]) for h in hcs]
    v["hard_cores"] = [h for h in v["hard_cores"] if h["inst"] not in X]
    n0 = len(v["internal_stations"])
    v["internal_stations"] = [e for e in v["internal_stations"] if not (ends(e) & set(X))]
    r["stations_removed"] = n0 - len(v["internal_stations"])
    n0 = len(v["clock"]["taps"])
    v["clock"]["taps"] = [x for x in v["clock"]["taps"] if x["name"].split(".")[0] not in X]
    r["taps_removed"] = n0 - len(v["clock"]["taps"])
    for x in X:
        CE.get(t, {}).pop(x, None)
        CC[t].pop(x, None)
    nref = 0
    for c, ports in CC[t].items():
        for po in list(ports):
            keep = [y for y in ports[po] if y.split(":", 1)[-1].split(".")[0] not in X]
            nref += len(ports[po]) - len(keep)
            ports[po] = keep
    r["core_conns_refs_removed"] = nref
    for c in v["contents"]:
        if c["inst"] in X:
            c["note"] = (c.get("note", "") + " | DIE-HBM-29 (COORD 21:25 ruling 4): folded into the hub as soft logic "
                         "(was a hard core 362.88x276.48, fill 0.060; hub glue run stays <= 400k cells)")
    v["note"] = v.get("note", "") + " | DIE-HBM-29 xq_pegress folded into hub soft logic (2 hard cores removed)"
    rep["types"][t] = r

(D / "die_plan.json").write_text(json.dumps(P, indent=1))
(D / "core_conns.json").write_text(json.dumps(CC, indent=1))
(D / "clock_entries.json").write_text(json.dumps(CE, indent=1))
M = json.loads(SMAP.read_text())
mv = []
for h in ("NW", "NE"):
    for i in (0, 1):
        k = f"xq_{h}_p{i}_eg"
        mv.append(dict(key=k, before=M["parts"][k], after=f"{h}_hub"))
        M["parts"][k] = f"{h}_hub"
M["note"] = "DIE-HBM-29 xq_pegress hub fold (soft leaf) | " + M["note"]
OMAP.write_text(json.dumps(M))
rep["map_moves"] = mv
(D / "xq_fold_report.json").write_text(json.dumps(rep, indent=1))
print(json.dumps(rep, indent=1))
