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
report=dict(scope='ACTUAL post-DPL FF data cones; macro F6, reset405, clock and timing remain separate gates',registers=len(targets),endpoint_arcs=sum(len(t['src']) for t in targets.values()),selected=len(selected),missing_selected=missing,max_hop_um=maxall,over405=dict(hist),selected_groups=group,worst_edges=sorted(bad,key=lambda r:-r['distance_um'])[:50])
Path(sys.argv[3]).write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='worst_edges'},indent=1))
