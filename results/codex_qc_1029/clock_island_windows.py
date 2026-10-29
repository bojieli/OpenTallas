#!/usr/bin/env python3
"""Declare top-owned QC clock islands in glue; never cut hard-core OBS."""
import argparse
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
for name in ('plan','bodies','tools','out'):
    ap.add_argument('--'+name,type=Path,required=True)
ap.add_argument('--landing-infra',action='store_true',help='Include real scalar landing contract pin rectangles')
ap.add_argument('--windows-only',action='store_true')
a = ap.parse_args()
sys.path.insert(0,str(a.tools))
import schema as S
import die_trial as DT
plan = S.Plan(S.load(a.plan),a.plan)
bodies = json.loads(a.bodies.read_text())['sites']
a.out.mkdir(parents=True,exist_ok=True)
# Body sites are coordinates prescribed by the plan/body-bay constructor,
# not a P&R placement. The source body is 1.62 x .27um; island helper takes
# its centre and pads outward by the preexisting platform snap+stack margin.
sites = dict(schema='ot_clock_sites/1',sites=[dict(name=name,kind='partition',
    xy_um=[xy[0]+.81,xy[1]+.135]) for name,xy in sorted(bodies.items())])
(a.out/'clock_island_sites.json').write_text(json.dumps(sites)+'\n')
windows,records = DT.island_windows(plan,DT.load_island_sites([a.out/'clock_island_sites.json']))
blocked = [dict(source=r['source'],part=h['part'],cores=h['in_core'])
           for r in records for h in r['parts'] if h['in_core']]
outside = [r['source'] for r in records if not r['parts']]
receipt = dict(schema='ot_island_windows/1',source=str(a.bodies),sites=len(bodies),
    policy='12.2a top-owned clock-only glue island; preserve all hard-core OBS',
    types=len(windows),windows=windows,blocked=blocked,outside=outside,
    assumption='planned 1.62x.27um clock bodies; .5um snap+.25um stack margin')
(a.out/'island_windows.json').write_text(json.dumps(receipt)+'\n')
cell_windows={}
for record in records:
    entries=[]
    for part in record['parts']:
        x0,y0,x1,y1=part['rect']
        points=[plan.to_die(part['part'],(x0,y0)),plan.to_die(part['part'],(x1,y1))]
        entries.append(dict(part=part['part'],type=part['type'],rect_type_um=part['rect'],
            rect_die_um=[min(p[0] for p in points),min(p[1] for p in points),
                         max(p[0] for p in points),max(p[1] for p in points)],in_core=part['in_core']))
    cell_windows[record['source'].split(':',1)[1]]=entries
(a.out/'cell_windows.json').write_text(json.dumps(dict(cells=cell_windows,
    source='DT.island_windows exact119 planned body-site holes; all coordinates um'))+'\n')
print('QC_ISLAND_WINDOWS',len(bodies),'sites',len(windows),'types',
      sum(map(len,windows.values())),'windows',len(blocked),'hardcorehits',len(outside),'outside')
if blocked or outside:
    raise SystemExit(1)
if a.windows_only:
    raise SystemExit(0)
# One master for each type, with identical island holes in every instance.
mods=DT.standin_module_names(plan)
(a.out/'abstracts').mkdir(exist_ok=True)
for tn in sorted(plan.types):
    text,_=DT.abstract_lef(plan,tn,islands=windows.get(tn),module_name=mods[tn],landing_infra=a.landing_infra)
    (a.out/'abstracts'/f'{mods[tn]}.lef').write_text(text)
print('QC_ISLAND_ABSTRACTS_READY',len(plan.types),'no hard-core cutouts')
