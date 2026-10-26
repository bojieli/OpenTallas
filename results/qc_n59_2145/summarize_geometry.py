"""Summarize actual complete N59 FF cones; every failing edge stays visible."""
import json,re,sys
from pathlib import Path
from collections import Counter
p=json.load(open(sys.argv[1]));model=json.load(open(sys.argv[2]));pos=p['positions'];targets=p['targets'];norm=lambda n:n.replace('\\','');names={norm(n):n for n in targets};selected={};missing=[]
for r in model['stations']:
 n=norm(r['name']);actual=n
 if n not in names:
  m=re.fullmatch(r'(u_bound\.u_pd([13])_[^.]+)\.r\[(\d+)\]\$_DFF_P_',n)
  if m and int(m[3])==int(m[2])-1:actual=m[1]+'.q$_DFF_P_'
  elif n=='u_bound.u_core.u_svc.dr_o[516]$_DFF_PN0_':actual='u_bound.u_core.u_svc.g_emb_relay.em_c[0][4]$_DFF_PN0_'
 if actual not in names:missing.append(n)
 else:selected[names[actual]]=r['group']
def distance(a,b):return abs(pos[a][0]-pos[b][0])+abs(pos[a][1]-pos[b][1])
bad=[];hist=Counter();group={};maxall=0
for sink,t in targets.items():
 for src in t['src']:
  d=distance(sink,src);maxall=max(maxall,d)
  if d>405:
   category='selected' if sink in selected or src in selected else 'other'
   hist[category]+=1;bad.append(dict(src=src,sink=sink,distance_um=round(d,3),category=category))
for n,k in selected.items():
 t=targets[n];near=t['src']+t['dst'];w=max((distance(n,s) for s in near),default=0)
 a=group.setdefault(k,dict(count=0,over405=0,max_hop_um=0));a['count']+=1;a['over405']+=w>405;a['max_hop_um']=max(a['max_hop_um'],w)
aux={}
for kind,limit in [('macro_cones',20),('reset_cones',405)]:
 rows=[];empty=0
 for pin,t in p.get(kind,{}).items():
  ds=[distance(pin,e) for e in t['ends']]
  if not ds:empty+=1;continue
  # SRAM outputs use their first/nearest capture, as the carried F6 gate.
  d=min(ds) if t.get('direction')=='OUTPUT' else max(ds)
  rows.append(dict(pin=pin,distance_um=round(d,3),endpoints=len(ds)))
 aux[kind]=dict(pins=len(p.get(kind,{})),empty_endpoint_cones=empty,limit_um=limit,max_um=max((r['distance_um'] for r in rows),default=0),over_limit=sum(r['distance_um']>limit for r in rows),worst=sorted(rows,key=lambda r:-r['distance_um'])[:30])
report=dict(scope='ACTUAL post-DPL complete FF data, macro F6 and reset cones; clock/timing remain separate gates',auxiliary_geometry=aux,registers=len(targets),endpoint_arcs=sum(len(t['src']) for t in targets.values()),selected=len(selected),missing_selected=missing,max_hop_um=maxall,over405=dict(hist),selected_groups=group,worst_edges=sorted(bad,key=lambda r:-r['distance_um'])[:50])
Path(sys.argv[3]).write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='worst_edges'},indent=1))
