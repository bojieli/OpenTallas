#!/usr/bin/env python3
"""Fleet diagnostic: reassign equal-shape children among legal slots to reduce reach debt."""
import argparse,json,random,math,collections,time,hashlib
from pathlib import Path
from qc_safe_graph import extract,ROOT
p=argparse.ArgumentParser();p.add_argument('witness');p.add_argument('--plan',required=True);p.add_argument('--out',required=True);p.add_argument('--seed',type=int,default=1);p.add_argument('--stale',type=int,default=100000);a=p.parse_args()
raw=Path(a.witness).read_bytes();d=json.loads(raw);assert not d.get('unknown_endpoint_rectangle_relaxation'),'center-based swap cost cannot consume relaxed endpoint witnesses';plan=json.loads(Path(a.plan).read_text());g=extract();c=g['contract'];assert abs(d['outline_um']['w']-3153.6)<1e-6
cols=[172.8+i*777.6 for i in range(4)];knots=sorted([(0,0),(c['outline_um']['w'],3153.6)]+[(x+t,y+t)for x,y in zip(sorted(set(v['at'][0]for v in c['tiles'])),cols)for t in [0,457.92]])
def mx(x):
 for(oa,na),(ob,nb)in zip(knots,knots[1:]):
  if oa-1e-5<=x<=ob+1e-5:return na+(x-oa)*(nb-na)/(ob-oa)
fixed={n:(mx(v['at'][0]),v['at'][1])for n,v in g['ports'].items()};placed={v['inst']:v for v in d['placement']};pos={n:tuple(v['at'])for n,v in placed.items()};assets={};bounds={}
for master,v in plan['native_pin_assets'].items():
 rawasset=(ROOT/v['path']).read_bytes();assert hashlib.sha256(rawasset).hexdigest()==v['sha256'];assets[master]=json.loads(rawasset)['pins']
for bus in plan['bindings']:
 src,dst=bus['src'],bus['dst']
 if src.get('master')not in assets or dst.get('master')not in assets:continue
 key=src['inst'],dst['inst'];b=bounds.setdefault(key,[-1e30]*4);starts=[e.get('range',[0,bus['bits']-1])[0]for e in [src,dst]]
 for i in range(bus['bits']):
  pts=[assets[e['master']][e['port']+f'[{lo+i}]']['centers_um'][0]for e,lo in zip([src,dst],starts)]
  dx,dy=[x-y for x,y in zip(*pts)]
  for k,(sx,sy)in enumerate([(1,1),(1,-1),(-1,1),(-1,-1)]):b[k]=max(b[k],sx*dx+sy*dy)
edges=d['edges'];incident=collections.defaultdict(set)
for i,e in enumerate(edges):
 for n in [e['src'],e['dst']]:incident[n].add(i)
def cost(i):
 e=edges[i];src,dst=e['src'],e['dst'];b=bounds.get((src,dst))
 if b is not None:
  dx,dy=[x-y for x,y in zip(pos[src],pos[dst])];length=max(sx*dx+sy*dy+off for off,(sx,sy)in zip(b,[(1,1),(1,-1),(-1,1),(-1,-1)]))
 else:
  def center(n):return (pos[n][0]+placed[n]['w']/2,pos[n][1]+placed[n]['h']/2)if n in pos else fixed[n]
  length=sum(abs(x-y)for x,y in zip(center(src),center(dst)))
 return max(0,length-e['reach_target_um'])
costs=[cost(i)for i in range(len(edges))];start=sum(costs);groups=collections.defaultdict(list)
for n,v in placed.items():groups[v['w'],v['h']].append(n)
groups=[v for v in groups.values()if len(v)>1];rng=random.Random(a.seed);stale=0;accepted=0;trials=0;started=time.time()
while stale<a.stale:
 group=rng.choices(groups,weights=[len(v)**2 for v in groups])[0];x,y=rng.sample(group,2);ids=incident[x]|incident[y];old=sum(costs[i]for i in ids);pos[x],pos[y]=pos[y],pos[x];fresh={i:cost(i)for i in ids};trials+=1
 if sum(fresh.values())<old-1e-7:
  for i,value in fresh.items():costs[i]=value
  accepted+=1;stale=0
  if accepted%100==0:print('SWAP_PROGRESS',accepted,'overrun',sum(costs),flush=True)
 else:pos[x],pos[y]=pos[y],pos[x];stale+=1
for n,v in placed.items():v['at']=list(pos[n])
d['placement']=list(placed.values());d['reach_violations']=[dict(edge=e,overrun_um=round(costs[i],6))for i,e in enumerate(edges)if costs[i]>1e-7];d['total_overrun_um']=sum(costs);d['release_ready']=False;d['swap_optimization']=dict(input_sha256=hashlib.sha256(raw).hexdigest(),initial_overrun_um=start,final_overrun_um=sum(costs),accepted=accepted,trials=trials,seed=a.seed,wall_s=time.time()-started,scope='equal-shape legal-slot reassignment; all physical clock/reset refs unqualified; reach is still diagnostic')
Path(a.out).write_text(json.dumps(d,indent=1)+'\n');print('SWAP_DONE',d['swap_optimization'],flush=True)
