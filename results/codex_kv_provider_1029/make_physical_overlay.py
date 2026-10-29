#!/usr/bin/env python3
"""Reserve actual clock/provider body islands once per repeated partition type."""
import argparse,collections,copy,hashlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--constraints',required=True);p.add_argument('--placements',required=True);p.add_argument('--tools',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools);import schema,die_trial
raw=json.load(open(a.plan));P=schema.Plan(raw,Path(a.plan));g=json.load(open(a.constraints));pl=json.load(open(a.placements));assert not pl['failed'];D=g['dbu'];groups=collections.defaultdict(list)
for q in pl['cells']:
 r=q['bbox_dbu'];groups[((r[2]-r[0])/D,(r[3]-r[1])/D)].append((((r[0]+r[2])/2/D,(r[1]+r[3])/2/D),'provider:'+q['inst']))
for n,m,x,y,X,Y in g['existing_cells']:
 groups[((X-x)/D,(Y-y)/D)].append((((x+X)/2/D,(y+Y)/2/D),'clock:'+n))
win=collections.defaultdict(set);bad=[];records=[]
for wh,sites in groups.items():
 w,rr=die_trial.island_windows(P,sites,cell=wh)
 for tn,rs in w.items():win[tn].update(map(tuple,rs))
 for r in rr:
  for part in r['parts']:
   if part['in_core']:bad.append(dict(source=r['source'],part=part['part'],cores=part['in_core']))
 records.extend(rr)
assert not bad,('hard-core intersections',len(bad),bad[:5]);out=Path(a.out);out.mkdir(parents=True,exist_ok=True);overlay=copy.deepcopy(raw)
for tn,rs in win.items():
 old=overlay['partition_types'][tn]['clock'].get('die_islands_um',[]);overlay['partition_types'][tn]['clock']['die_islands_um']=sorted(set(map(tuple,old))|rs)
# Only the physical reservation field may change. Parent pins, core outlines,
# reset/START logic, count straps and every latency remain exact.
clean=copy.deepcopy(overlay)
for tn in win:
 if 'die_islands_um' in raw['partition_types'][tn]['clock']:clean['partition_types'][tn]['clock']['die_islands_um']=raw['partition_types'][tn]['clock']['die_islands_um']
 else:clean['partition_types'][tn]['clock'].pop('die_islands_um')
assert clean==raw
(out/'plan_reserved.json').write_text(json.dumps(overlay,separators=(',',':'))+'\n');payload=dict(schema='ot_island_windows/1',meta=dict(source_plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),provider_cells=len(pl['cells']),clock_cells=len(g['existing_cells']),types=len(win),windows=sum(map(len,win.values())),hardcore_hits=0,pins_cycles_hardcore_delta=0),windows={k:sorted(v) for k,v in win.items()});(out/'island_windows.json').write_text(json.dumps(payload,separators=(',',':'))+'\n');(out/'summary.json').write_text(json.dumps(payload['meta'],indent=1)+'\n');print(json.dumps(payload['meta'],indent=1))
