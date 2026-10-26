#!/usr/bin/env python3
"""All-incident read-leaf placement alternatives; unchanged graph, shape and root count.
Planning only: exact capture grant, frozen peer-span pins for other ports; no RTL adoption.
"""
import argparse,collections,copy,gzip,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
sys.path.insert(0,str(Path(__file__).resolve().parent))
import a2f_hub_faces as HF
R=HF.R;ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/arch/s81_vm_margin_0253'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--passes',type=int,default=30);ap.add_argument('--case',choices=['baseline','face','balanced','internal'],required=True);a=ap.parse_args()
 base=json.loads((OUT/'baseline_gapE.json').read_text());W,H=base['rectangle_um']
 P,nets,_,_,_,_=HF.build_split4(W,[['f0','f1','f2','f3','f4','f5','f6','f7'],['ctl','fj','meta']],True,False,True)
 nets=HF.hop1(P,nets);ids={l['name']:i for i,l in enumerate(P.leaves)}
 assert set(base['placement'])=={P.leaves[i]['name'] for i in P.pos}
 for name,v in base['placement'].items():
  i=ids[name];assert P.leaves[i]['master']==v[0] and [P.leaves[i]['w'],P.leaves[i]['h']]==v[3:5]
  P.pos[i]=(v[1],v[2],v[5],v[6])
 assigned=json.loads((ROOT/base['assigned_pins']['path']).read_text());HF.install_spans(base['spans'],assigned)
 R.connections(P,nets,W,H);place=copy.deepcopy(R._last_port_place);models=R.pin_models(P.leaves)
 def pin(e,pos=None):
  i,p,b=e;x,y,fx,fy=pos or P.pos[i]
  return R.pin_xy(P.leaves[i],models[P.leaves[i]['master']],p,b,x,y,fx,fy)
 read={i for i in P.pos if 'read_q' in P.leaves[i]['master']}
 incident=collections.defaultdict(list);portpins=collections.defaultdict(dict);nraw=0
 for es in nets:
  lv=[e for e in es if e[0]>=0]
  if not lv:continue
  for i,p,b in es:
   if i<0:portpins[p][b]=place[(nraw,p)]
  for e in lv:
   if e[0] not in read:continue
   for other in es:
    if other[0]==e[0]:continue
    q=pin(other) if other[0]>=0 else place[(nraw,other[1])]
    incident[e[0]].append((e,q,other[0]<0,other[1]))
  nraw+=1
 groups=collections.defaultdict(list)
 for i in sorted(read):groups[(P.leaves[i]['w'],P.leaves[i]['h'])].append(i)
 changes=[];costs={}
 if a.case!='baseline':
  wp={'face':8.,'balanced':1.,'internal':.125}[a.case];old=copy.deepcopy(P.pos)
  for dims,group in groups.items():
   cost=np.zeros((len(group),len(group)))
   for ri,i in enumerate(group):
    for cj,j in enumerate(group):
     for e,q,ip,p in incident[i]:
      xy=pin(e,old[j]);cost[ri,cj]+=(wp if ip else 1.)*(abs(xy[0]-q[0])+abs(xy[1]-q[1]))
   row,col=linear_sum_assignment(cost)
   for ri,cj in zip(row,col):
    i,j=group[ri],group[cj];P.pos[i]=old[j]
    if i!=j:changes.append([P.leaves[i]['name'],list(old[i]),list(old[j])])
   costs[str(dims)]=dict(before=float(cost.trace()),after=float(cost[row,col].sum()))
 # Freeze every parent bit at its baseline coordinate; span repacking would hide port changes.
 grant={'outline_um':[W,H],'ports':{}}
 for pname,bb in portpins.items():
  face=next(v[0] for k,v in sorted(base['spans'].items(),key=lambda kv:-len(kv[0])) if pname.startswith(k));per=[]
  for b in range(max(bb)+1):
   x,y=bb.get(b,(0.,0.));c=y if face in 'WE' else x;depth=2*{'W':x,'E':W-x,'N':H-y,'S':y}[face];per.append([face,'PLANNED',c,depth])
  grant['ports'][pname]={'bits':len(per),'per_bit':per}
 R.connections=R._base_connections;HF.install_spans(base['spans'],grant)
 bad,outside=P.check(W,H);assert bad==0 and outside==0,(bad,outside)
 conns,faces=R.connections(P,nets,W,H);pair=collections.defaultdict(list)
 for i,rows in incident.items():
  for e,q,ip,p in rows:
   x=pin(e);pair['parent' if ip else 'internal'].append(abs(x[0]-q[0])+abs(x[1]-q[1]))
 status=collections.Counter()
 for line in gzip.open(R.AREA/'a2_pin_join.jsonl.gz','rt'):
  if line.strip():status[json.loads(line)['status']]+=1
 result=dict(schema='opentallas.s81.vm-read-affinity-margin.v1',case=a.case,status='SCREEN_ONLY_NOT_ADOPTED',outline_um=[W,H],leaves=len(P.pos),bank128=sum('static_bank128' in P.leaves[i]['master'] for i in P.pos),nets=len(nets),connections=len(conns),changed=changes,assignment_cost=costs,legality=dict(spacing=bad,outside=outside),parent_port_bits={k:len(v) for k,v in portpins.items()},graph_status=dict(status),direct_read_incident_um={k:dict(max=max(v),mean=sum(v)/len(v),bits=len(v)) for k,v in pair.items()},cut_scope='Capture exact grant; all other parent bits frozen at baseline peer-span-planned positions. No new full parent pin grant.',baseline_source_tools_match={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in base['source_tools'].items()},placement={P.leaves[i]['name']:[P.leaves[i]['master']]+list(P.rect(i))+list(P.pos[i][2:]) for i in sorted(P.pos)},not_claimed=['Full native RTL parent/current production graph equivalence','Clock/reset routes, phi-R delivery or PG solve','GRT/DRT/timing closure','Fixed schedule/compiler price qualification'])
 print('ROUTING',a.case,'leaves',len(P.pos),'nets',len(nets),'moved',len(changes),flush=True)
 result['cuts']=R.routed_report(P,nets,W,H,100.,pg=R.pg_plan(P,W,H),passes=a.passes);result['passes']=a.passes;result['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 (OUT/(a.case+'.json')).write_text(json.dumps(result,indent=1)+'\n')
 import a2_floorplan as FP
 FP.svg(P,W,H,str(OUT/(a.case+'.svg')))
 print(a.case,result['cuts'],flush=True)
if __name__=='__main__':main()
