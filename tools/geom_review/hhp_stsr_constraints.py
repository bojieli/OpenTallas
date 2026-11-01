#!/usr/bin/env python3
import sys,json,re,argparse
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument("--dump-root",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);args=ap.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'autopilot'));import geom_rules as G
out=[]
for variant in ['a','b']:
 D=G.Design(args.dump_root/('hhp'+variant)/'geom.tsv'); targets=[k for k,c in D.cells.items() if re.search(r'\.st_sr\\\[[01]\\\]',c[6])]
 def point(ref):
  kind,k=ref
  if kind=='i': c=D.cells[k];return dict(kind='sequential',instance=c[6],xy=list(G.ctr(c)))
  p=D.pin_by_k[k];return dict(kind='boundary_pin',pin=p['name'],io=p['io'],xy=[p['x'],p['y']],layer=p['layer'])
 rows=[]
 for target in targets:
  row=dict(instance=D.cells[target][6],xy=list(G.ctr(D.cells[target])))
  for direction in ['incoming','outgoing']:
   starts=[n for n,clk in D.cell_in[target] if not clk] if direction=='incoming' else D.drives[target]
   found={};visited=set();front=[(n,True) for n in starts]
   while front:
    n,bufonly=front.pop(); key=(n,bufonly)
    if key in visited:continue
    visited.add(key)
    refs=([D.nets[n][1]] if D.nets[n][1] else []) if direction=='incoming' else D.nets[n][2]
    if direction=='incoming' and n in D.multi_drv:refs=[('i',k,False) for k in D.multi_drv[n]]
    for ref in refs:
     kind,k,clock=ref
     if clock:continue
     if kind=='p' or D.kind(k)=='S':
      f=found.setdefault((kind,k),dict(point((kind,k)),buffer_only_path=False));f['buffer_only_path']|=bufonly;continue
     if D.kind(k) in 'BLK':
      ns=([nn for nn,clk in D.cell_in[k] if not clk] if direction=='incoming' else D.drives[k]);front.extend((nn,bufonly and D.kind(k)=='B') for nn in ns)
   vals=list(found.values())
   for f in vals:f['distance_um']=sum(abs(x-y) for x,y in zip(row['xy'],f['xy']))
   row[direction]=sorted(vals,key=lambda v:v['distance_um'],reverse=True)
  rows.append(row)
 out.append(dict(variant=variant,rows=rows,scope='all non-clock combinational incidence, stops first sequential or boundary pin; reset+data both retained, no per-terminal D/reset classification available in TSV'))
print(json.dumps([{**{k:v for k,v in o.items() if k!='rows'},'summary':[dict(instance=r['instance'],xy=r['xy'],incoming=len(r['incoming']),outgoing=len(r['outgoing']),worst_in=r['incoming'][:2],worst_out=r['outgoing'][:4],pins=[f for dr in ['incoming','outgoing'] for f in r[dr] if f['kind']=='boundary_pin']) for r in o['rows']]} for o in out],indent=2))
json.dump(out,args.out.open('w'),indent=2)
