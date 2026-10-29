#!/usr/bin/env python3
"""QC-IMPORT-1: ot_clock_sites/1 for every placed provider body (actual body size) + combined island-window census
(clock 44,590 planned bodies + provider 48,259 actual bodies) on the QC plan of record, via main die_trial.island_windows.
usage: provider_sites.py TOOLS PLAN PLACEMENTS CLOCK_SITES OUTDIR"""
import collections, hashlib, json, sys
from pathlib import Path
tools, plan, placements, clock_sites, out = sys.argv[1:6]
sys.path.insert(0, tools)
import schema as S, die_trial as DT
out = Path(out); out.mkdir(parents=True, exist_ok=True)
x = json.load(open(placements)); assert not x["failed"]
D = x["dbu"]
sites = [dict(name=c["inst"], kind="partition",
              xy_um=[(c["bbox_dbu"][0] + c["bbox_dbu"][2]) / 2 / D, (c["bbox_dbu"][1] + c["bbox_dbu"][3]) / 2 / D],
              cell_um=[(c["bbox_dbu"][2] - c["bbox_dbu"][0]) / D, (c["bbox_dbu"][3] - c["bbox_dbu"][1]) / D])
         for c in x["cells"]]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
(out / "provider_sites.json").write_text(json.dumps(dict(schema="ot_clock_sites/1", source=placements,
    placements_sha256=sha(placements), sites=sites), separators=(",", ":")))
p = Path(plan).resolve()
P = S.Plan(S.load(p), p)
res = {}
for tag, files in (("clock", [clock_sites]), ("provider", [out / "provider_sites.json"]),
                   ("combined", [clock_sites, out / "provider_sites.json"])):
    ss = DT.load_island_sites([str(f) for f in files])
    win, recs = DT.island_windows(P, ss)
    in_core = sum(1 for r in recs for h in r["parts"] if h["in_core"])
    outside = sum(1 for r in recs if not r["parts"])
    res[tag] = dict(sites=len(ss), types=len(win), windows=sum(map(len, win.values())), in_core=in_core,
                    outside_partitions=outside)
    if tag == "combined":
        (out / "combined_island_windows.json").write_text(json.dumps(dict(schema="ot_island_windows/1",
            windows=win, census=res), separators=(",", ":")))
res["plan_sha256"] = sha(p); res["clock_sites_sha256"] = sha(clock_sites)
(out / "island_census.json").write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps(res, indent=1))
