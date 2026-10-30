#!/usr/bin/env python3
"""DIE-QC-50/gen47b: island sites for the fresh plan_qc49 native target (QC-IMPORT-1 provider_sites.py recipe).
clock  = the 48,296 gen47 clock bodies (actual bbox from the gen47 export of build2/clock_native.odb)
provider = the 50,020 placed provider bodies (gen47 pimpC2 placements, actual bbox)
Combined windows via main die_trial.island_windows (per-site cell_um opt-in). HOLD on any in-core / outside site.
usage: sites47b.py TOOLS PLAN CONSTRAINTS PLACEMENTS OUTDIR"""
import collections, hashlib, json, sys
from pathlib import Path
tools, plan, cons, placements, out = sys.argv[1:6]
sys.path.insert(0, tools)
import schema as S, die_trial as DT
out = Path(out); out.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
c = json.load(open(cons)); D = c['dbu']
def site(name, r):
    return dict(name=name, kind='partition', xy_um=[(r[0] + r[2]) / 2 / D, (r[1] + r[3]) / 2 / D],
                cell_um=[(r[2] - r[0]) / D, (r[3] - r[1]) / D])
clk = [site(e[0], e[2:6]) for e in c['existing_cells']]
x = json.load(open(placements)); assert not x['failed'] and x['dbu'] == D
prov = [site(q['inst'], q['bbox_dbu']) for q in x['cells']]
for tag, ss, src in (('clock', clk, cons), ('provider', prov, placements)):
    (out / f'{tag}_sites.json').write_text(json.dumps(dict(schema='ot_clock_sites/1', source=src, source_sha256=sha(src),
                                                         sites=ss), separators=(',', ':')))
p = Path(plan).resolve(); P = S.Plan(S.load(p), p)
res = {}
for tag, files in (('clock', ['clock']), ('provider', ['provider']), ('combined', ['clock', 'provider'])):
    ss = DT.load_island_sites([str(out / f'{f}_sites.json') for f in files])
    win, recs = DT.island_windows(P, ss)
    in_core = [r['source'] for r in recs for h in r['parts'] if h['in_core']]
    outside = [r['source'] for r in recs if not r['parts']]
    inside = sum(1 for r in recs if r['parts'])
    res[tag] = dict(sites=len(ss), sites_in_partitions=inside, types=len(win), windows=sum(map(len, win.values())),
                    in_core=len(in_core), in_core_sample=in_core[:20], outside_partitions=len(outside))
    if tag == 'combined':
        (out / 'combined_island_windows.json').write_text(json.dumps(dict(schema='ot_island_windows/1', windows=win,
                                                                          census=res), separators=(',', ':')))
res.update(plan_sha256=sha(p), constraints_sha256=sha(cons), placements_sha256=sha(placements),
           tools_note='main die_trial.island_windows / load_island_sites (cell_um opt-in)')
(out / 'island_census.json').write_text(json.dumps(res, indent=1) + '\n')
print(json.dumps(res, indent=1))
