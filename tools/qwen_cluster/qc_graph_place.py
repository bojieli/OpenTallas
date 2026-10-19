#!/usr/bin/env python3
"""Connectivity-driven diagnostic parent placement. Fleet only, never emits a kit.
Logical regional clocks remain unchanged. Hard children may cross geometric seams.
Corridor/row-gap route distances avoid the A0 obstacles. Every >405um segment is
reported as relay debt, including landed banks; no path is silently exempted.
"""
import argparse,json,math,random,collections
from pathlib import Path
from qc_safe_graph import extract,ROOT
G=43.2;GAP=20

def clash(a,b):
 return not(a[0]+a[2]+GAP<=b[0]+1e-6 or b[0]+b[2]+GAP<=a[0]+1e-6 or a[1]+a[3]+GAP<=b[1]+1e-6 or b[1]+b[3]+GAP<=a[1]+1e-6)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--step',type=float,default=777.6);ap.add_argument('--seed',type=int,default=0);ap.add_argument('--out',required=True);ap.add_argument('--iterations',type=int,default=12000);a=ap.parse_args();rng=random.Random(a.seed)
 graph=extract();assert not graph['unresolved'],graph['unresolved'];c=graph['contract'];oldx=sorted(set(t['at'][0]for t in c['tiles']));cols=[129.6+i*a.step for i in range(4)];W=math.ceil((cols[-1]+457.92+129.6)/G-1e-8)*G;H=c['outline_um']['h']
 knots=sorted([(0,0),(c['outline_um']['w'],W)]+[(x+d,y+d)for x,y in zip(oldx,cols)for d in [0,457.92]])
 def mx(x):
  for (oa,na),(ob,nb)in zip(knots,knots[1:]):
   if oa-1e-5<=x<=ob+1e-5:return na+(x-oa)*(nb-na)/(ob-oa)
  raise ValueError(x)
 def mp(p):return [mx(p[0]),p[1]]
 tileobs=[(cols[int(t['inst'][4])],t['at'][1],457.92,1166.4)for t in c['tiles']]
 corr=[(0,cols[0])]+[(cols[i]+457.92,cols[i+1])for i in range(3)]+[(cols[-1]+457.92,W)]
 rows=sorted(set(t['at'][1]for t in c['tiles']));channels=[(0,rows[0])]+[(rows[i]+1166.4,rows[i+1])for i in range(3)]+[(rows[-1]+1166.4,H)]
 cy=[(lo+hi)/2 for lo,hi in channels];cx=[(lo+hi)/2 for lo,hi in corr]
 def route(p,q):
  def anchors(v):
   avail=[i for i,(lo,hi)in enumerate(corr)if lo-1e-5<=v[0]<=hi+1e-5]
   if not avail:
    if not any(lo-1e-5<=v[1]<=hi+1e-5 for lo,hi in channels):return []
    avail=range(5)
   return [(i,abs(v[0]-cx[i]))for i in avail]
  ans=1e9
  for i,di in anchors(p):
   for j,dj in anchors(q):
    middle=abs(p[1]-q[1])if i==j else abs(cx[i]-cx[j])+min(abs(p[1]-y)+abs(q[1]-y)for y in cy)
    ans=min(ans,di+dj+middle)
  return ans
 jobs={};groups={};fixed={}
 for name,p in graph['ports'].items():fixed[name]=mp(p['at'])
 for name,n in graph['nodes'].items():
  if n['bits']<=1:continue
  if n['kind'].startswith('qfd_c_land_'):
   group=[]
   for part in range(2):
    key=name+f'_p{part}';jobs[key]=dict(logical=name,part=part,w=64.8,h=129.6,target=mp(n['at']),region=n['region'],kind=n['kind']);group.append(key)
   groups[name]=group
  else:
   # Full-width station now also meets <=6pins/um: 514/516 on N/S90.72-wide faces.
   # xstn additionally exports the508bit tap on a129.6-high side.
   w,h=(90.72,129.6)if'xstn'in n['kind']else(90.72,64.8)
   jobs[name]=dict(logical=name,w=w,h=h,target=mp(n['at']),region=n['region'],kind=n['kind']);groups[name]=[name]
 edges=[]
 for e in graph['edges']:
  ss=groups.get(e['src'],[e['src']]);dd=groups.get(e['dst'],[e['dst']])
  pairs=zip(ss,dd)if len(ss)==len(dd)==2 else((s,d)for s in ss for d in dd)
  for src,dst in pairs:edges.append(dict(e,src=src,dst=dst))
 adj=collections.defaultdict(list)
 for i,e in enumerate(edges):adj[e['src']].append(i);adj[e['dst']].append(i)
 # Grid-origin candidate sets from actual area/pin-sized geometry. Filter A0+20um channels once.
 candidates={}
 for shape in set((j['w'],j['h'])for j in jobs.values()):
  w,h=shape;cs=[]
  for ix in range(1,math.floor((W-GAP-w)/G)+1):
   for iy in range(1,math.floor((H-GAP-h)/G)+1):
    rect=(ix*G,iy*G,w,h)
    if not any(clash(rect,o)for o in tileobs):cs.append((ix*G,iy*G))
  candidates[shape]=cs
 loc={};buckets=collections.defaultdict(set);B=172.8
 def bins(rect):
  x,y,w,h=rect
  return[(i,j)for i in range(math.floor((x-GAP)/B),math.floor((x+w+GAP)/B)+1)for j in range(math.floor((y-GAP)/B),math.floor((y+h+GAP)/B)+1)]
 def insert(k,p):
  loc[k]=p;j=jobs[k]
  for b in bins((*p,j['w'],j['h'])):buckets[b].add(k)
 def remove(k):
  p=loc.pop(k);j=jobs[k]
  for b in bins((*p,j['w'],j['h'])):buckets[b].discard(k)
 def legal(k,p,ignore=()):
  j=jobs[k];r=(*p,j['w'],j['h']);seen=set()
  for b in bins(r):seen.update(buckets[b])
  for other in seen:
   if other==k or other in ignore:continue
   v=jobs[other]
   if clash(r,(*loc[other],v['w'],v['h'])):return False
  return True
 def point(k,proposed=None):
  if k in fixed:return fixed[k]
  j=jobs[k];p=proposed if proposed is not None else loc.get(k)
  return [p[0]+j['w']/2,p[1]+j['h']/2]if p else j['target']
 def edgecost(d):return d+max(0,d-405)*8
 def score(k,p):
  q=point(k,p);s=0
  for ei in adj[k]:
   e=edges[ei];other=e['dst']if e['src']==k else e['src'];s+=edgecost(route(q,point(other)))
  # Only a weak tie-break towards the old site. No rectangular region seam constraint.
  return s+.02*(abs(q[0]-jobs[k]['target'][0])+abs(q[1]-jobs[k]['target'][1]))
 unplaced=[]
 order=list(jobs);rng.shuffle(order);order.sort(key=lambda k:(-sum(v in fixed for ei in adj[k]for v in [edges[ei]['src'],edges[ei]['dst']]),-jobs[k]['h']))
 for k in order:
  j=jobs[k];cand=sorted(candidates[j['w'],j['h']],key=lambda p:score(k,p))
  for p in cand:
   if legal(k,p):insert(k,p);break
  else:unplaced.append(k)
 # Connectivity-aware legal coordinate descent then same-shape swaps. Relays remain explicit debt.
 keys=list(loc)
 for it in range(a.iterations):
  if not keys:break
  k=rng.choice(keys);j=jobs[k];old=loc[k]
  if it%4:
   cs=candidates[j['w'],j['h']];p=rng.choice(cs)
   if legal(k,p)and score(k,p)<score(k,old)-1e-6:remove(k);insert(k,p)
  else:
   others=[v for v in keys if v!=k and(jobs[v]['w'],jobs[v]['h'])==(j['w'],j['h'])]
   if not others:continue
   v=rng.choice(others);vp=loc[v]
   if not legal(k,vp,(v,))or not legal(v,old,(k,)):continue
   before=sum(edgecost(route(point(e['src']),point(e['dst'])))for ei in set(adj[k]+adj[v])for e in [edges[ei]])
   remove(k);remove(v);insert(k,vp);insert(v,old)
   after=sum(edgecost(route(point(e['src']),point(e['dst'])))for ei in set(adj[k]+adj[v])for e in [edges[ei]])
   if after>before+1e-6:remove(k);remove(v);insert(k,old);insert(v,vp)
 result=[]
 for e in edges:
  if(e['src']in jobs and e['src']not in loc)or(e['dst']in jobs and e['dst']not in loc):continue
  d=route(point(e['src']),point(e['dst']));result.append(dict(e,route_um=round(d,3),relay_edges_needed=max(0,math.ceil(d/315)-1),reach405_pass=d<=405))
 violations=[e for e in result if not e['reach405_pass']]
 reset=[dict(inst=k,region=n['region'],target=mp(n['at']))for k,n in graph['reset_nodes'].items()]
 out=dict(schema='opentallas.cb16.graph_place.v1',diagnostic_only=True,source=graph['source'],seed=a.seed,iterations=a.iterations,outline_um=dict(w=W,h=H),area_mm2=W*H/1e6,area_ratio=W/c['outline_um']['w'],tile_origins_x_um=cols,clock_domain_rule='logical region unchanged; hard child geometric regions may overlap, no inferred clock qualification',candidate_count=len(jobs),placed=len(loc),unplaced=unplaced,placement=[dict(jobs[k],inst=k,at=loc[k])for k in loc],edge_count=len(result),reach405_violations=len(violations),max_route_um=max(e['route_um']for e in result),edges=result,unhardened_resets=reset,release_ready=False)
 p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=1)+'\n')
 print('GRAPH_PLACE',a.step,a.seed,'outline',W,H,'placed',len(loc),'unplaced',len(unplaced),'edges',len(result),'reachfails',len(violations),'maxwire',out['max_route_um'])
if __name__=='__main__':main()
