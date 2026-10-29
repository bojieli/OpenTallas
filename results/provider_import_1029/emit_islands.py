#!/usr/bin/env python3
"""Request explicit type-union all-cell islands; never edit LEF/OBS here."""
import argparse,collections,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--placements',required=True);p.add_argument('--die-plan',required=True);p.add_argument('--tools',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools);import schema,die_trial
x=json.load(open(a.placements));assert not x['failed'],'cannot request incomplete all-cell import';P=schema.Plan(schema.load(a.die_plan),Path(a.die_plan));D=x['dbu'];groups=collections.defaultdict(list)
for c in x['cells']:
 r=c['bbox_dbu'];wh=((r[2]-r[0])/D,(r[3]-r[1])/D);groups[wh].append((((r[0]+r[2])/2/D,(r[1]+r[3])/2/D),c['inst']))
windows=collections.defaultdict(set);records=[];blocked=[];outside=[]
for wh,sites in groups.items():
 ww,rr=die_trial.island_windows(P,sites,cell=wh)
 for t,rects in ww.items():windows[t].update(map(tuple,rects))
 for record in rr:
  entries=[]
  for q in record['parts']:
   u,v,U,V=q['rect'];aa=P.to_die(q['part'],(u,v));bb=P.to_die(q['part'],(U,V));entries.append(dict(part=q['part'],type=q['type'],rect_type_um=q['rect'],rect_die_um=[min(aa[0],bb[0]),min(aa[1],bb[1]),max(aa[0],bb[0]),max(aa[1],bb[1])],in_core=q['in_core']))
   if q['in_core']:blocked.append(dict(inst=record['source'],part=q['part'],cores=q['in_core']))
  if not entries:
   xx,yy=record['xy_um'];channel=any(r['rect_um'][0]<=xx<=r['rect_um'][2] and r['rect_um'][1]<=yy<=r['rect_um'][3] for r in P.die.get('channels',[]) if r.get('rect_um'))
   if not channel:outside.append(record['source'])
  records.append(dict(inst=record['source'],parts=entries))
out=Path(a.out);out.mkdir(parents=True,exist_ok=True);payload=dict(schema='ot_island_windows/1',proposal_only=True,source=a.placements,policy='Explicit top-owned provider all-cell type-union windows; preserve every hard-core OBS; parent regenerates fresh abstracts before import',sites=len(x['cells']),types=len(windows),windows={t:sorted(w) for t,w in windows.items()},blocked=blocked,outside=outside)
json.dump(payload,open(out/'island_windows.json','w'),separators=(',',':'));json.dump(dict(cells={r['inst']:r['parts'] for r in records},source='actual all mapped provider body geometry + existing explicit island constructor'),open(out/'cell_windows.json','w'),separators=(',',':'));print(json.dumps(dict(cells=len(x['cells']),types=len(windows),windows=sum(map(len,windows.values())),hardcore_hits=len(blocked),outside=len(outside),verdict='PROPOSAL_ISLANDS_READY' if not blocked and not outside else 'HOLD_NO_IMPORT'),indent=2));raise SystemExit(bool(blocked or outside))
