import json,sys
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-head-collect-1030/tools/autopilot')
from geom_rules import Design,ctr
r=Path('/srv/opentallas-scratch2/claude/codex-head-collect-1030/serdes_reshape/geom_place');d=Design(r/'geom.tsv');out=[]
for p in d.pins:
 if p['io']!='INPUT' or not p['name'].startswith(('k_lo[','k_L[','k_v[','k_any')):continue
 front=[(d.pin_net[p['k']],0)];seen=set();cap={};comb=set()
 while front:
  n,lev=front.pop()
  if n in seen:continue
  seen.add(n)
  for kind,i,clock in d.nets[n][2]:
   if kind!='i' or clock:continue
   ck=d.kind(i)
   if ck=='S':cap[i]=lev
   elif ck not in ('M',):
    comb.add(i);front.extend((nn,lev+1) for nn in d.drives.get(i,[]))
 ds=[(abs(ctr(d.cells[i])[0]-p['x'])+abs(ctr(d.cells[i])[1]-p['y']),d.cells[i][6]) for i in cap]
 out.append(dict(port=p['name'],captures=len(cap),comb_cells=len(comb),levels=max(cap.values(),default=0),nearest_um=min(ds,default=(None,None)),farthest_um=max(ds,default=(None,None))))
x=dict(pins=len(out),max_farthest=max(out,key=lambda q:q['farthest_um'][0]),ports=out,basis='actual3place connectivity all comb paths to first sequential capture, diagnostic parent405budget')
(r/'internal_pin_cones.json').write_text(json.dumps(x,indent=1)+'\n');print(json.dumps({k:v for k,v in x.items() if k!='ports'}))
