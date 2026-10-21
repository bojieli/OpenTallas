"""Optimize source instance assignment on unchanged equal-outline legal slots."""
import json,copy,random,math,time,hashlib
from pathlib import Path
from collections import defaultdict
r=Path(__file__).resolve().parent;p=json.load(open(r/'input.json'));q=json.load(open(r/'candidate.json'));bs=q['blocks'];old=p['blocks'];xy=[[b['x'],b['y']]for b in bs];groups=defaultdict(list)
for i,b in enumerate(bs):
 if b['kind']not in('phy','ctrl'):groups[(b['kind'],b['w'],b['h'])].append(i)
groups=[g for g in groups.values()if len(g)>1];adj=[set()for b in bs];edges=[]
for n,l in enumerate(p['links']):
 ends=[]
 for e in l['e']:
  i=e[0];a=old[i];b=bs[i];ends.append((i,(e[2]-a['x'])/a['w']*b['w'],(e[3]-a['y'])/a['h']*b['h']));adj[i].add(n)
 edges.append((l['b'],ends))
def cost(n):
 w,((i,dx,dy),(j,DX,DY))=edges[n];return w*(abs(xy[i][0]+dx-xy[j][0]-DX)+abs(xy[i][1]+dy-xy[j][1]-DY))
costs=[cost(n)for n in range(len(edges))];total=sum(costs);initial=total;best=total;bestxy=copy.deepcopy(xy);rng=random.Random(1021);t0=time.monotonic();steps=0;accepted=0
while steps<250000 and time.monotonic()-t0<45:
 g=rng.choice(groups);i,j=rng.sample(g,2);ns=adj[i]|adj[j];before=sum(costs[n]for n in ns);xy[i],xy[j]=xy[j],xy[i];fresh={n:cost(n)for n in ns};delta=sum(fresh.values())-before
 temperature=initial/400*max(.002,1-steps/250000)**3
 if delta<=0 or rng.random()<math.exp(-delta/max(temperature,1)):
  total+=delta;costs=[fresh.get(n,v)for n,v in enumerate(costs)]if False else costs
  for n,v in fresh.items():costs[n]=v
  accepted+=1
  if total<best:best=total;bestxy=copy.deepcopy(xy)
 else:xy[i],xy[j]=xy[j],xy[i]
 steps+=1
for i,b in enumerate(bs):b['x'],b['y']=bestxy[i]
q['facts']['assignment_optimization']={'initial_weighted_manhattan_bit_um':initial,'final_weighted_manhattan_bit_um':best,'ratio':best/initial,'steps':steps,'accepted':accepted,'elapsed_s':time.monotonic()-t0,'same_outline_only':True,'scope':'MODELonly; identical slot geometry/bodies/capacity, source identities/ports preserved; fresh actualnominalrouting stillrequired'}
(r/'assigned.json').write_text(json.dumps(q,indent=1)+'\n');print(json.dumps(q['facts']['assignment_optimization']),flush=True)
# Reproject the exact same819 logical port identities into assigned boxes.
q['links']=copy.deepcopy(p['links'])
for l in q['links']:
 for k in('h','sp','s','L','station_dirs'):l.pop(k,None)
 for e in l['e']:
  a=old[e[0]];b=bs[e[0]];e[2]=round(b['x']+(e[2]-a['x'])/a['w']*b['w'],4);e[3]=round(b['y']+(e[3]-a['y'])/a['h']*b['h'],4)
q['facts']['die_um']=[33000,26000];q['facts']['physical72']={'scope':'MODELsameoutlineassignment,819nominalpaths; allactualviewpin/clock/relaybody/source/STAcalendarholds retained'}
(r/'route_input.json').write_text(json.dumps(q,indent=1)+'\n')
