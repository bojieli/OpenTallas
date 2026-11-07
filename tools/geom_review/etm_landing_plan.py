#!/usr/bin/env python3
"""Plan actual-checkpoint BKSEL ETM macroface clock corridors.

Read-only estimates: this does not edit a database, insert delay, or authorize
P&R. All candidate upstream nodes are evaluated independently. Buffer slots use
actual row segments/current cell occupancy and a 5um macro guard. Orthogonal
connections avoid macro bodies; they are planning paths, not global routes.
TT NLDM envelopes are from ASAP7 INVBUF RVT TT220122 at20ps input slew:
BUF24 max rise/fall delay33.0749ps at23.04fF, BUF8 30.4546ps at5.76fF.
A source slope0.25ps/fF approximates the additional existing-driver load.
Re-evaluate with actual propagated arrivals/load/slew before selecting a form.
"""
import argparse, heapq
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--layout',required=True)
ap.add_argument('--clocks',required=True)
ap.add_argument('--output',required=True)
ap.add_argument('--arrivals',help='Optional exact TT extraction TSV: name,rise,fall inps')
args=ap.parse_args()
import json, math, bisect
from collections import defaultdict
p=json.load(open(args.layout))
rows=p['rows']; occ=defaultdict(list)
for c in p['std_cells']:
 _,_,_,x,y,xx,yy=c
 r=round((y-4.32)/.27)
 for k in range(r,r+max(1,round((yy-y)/.27))): occ[k].append((x,xx))
for m in p['blocks']:
 _,_,x,y,xx,yy=m
 for r in range(len(rows)):
  ry=rows[r][2]
  if ry < yy+5 and ry+.27 > y-5: occ[round((ry-4.32)/.27)].append((x-5,xx+5))
for r in occ:
 a=sorted(occ[r]); out=[]
 for x,y in a:
  if out and x <=out[-1][1]+1e-5: out[-1]=(out[-1][0],max(y,out[-1][1]))
  else: out.append((x,y))
 occ[r]=out

def slot(tx,ty,w,maxdx=12,maxdy=6):
 best=None
 for r,row in enumerate(rows):
  y=row[2]
  if abs(y-ty)>maxdy:continue
  intervals=[(row[1],row[1])]+[(max(a,row[1]),min(b,row[3])) for a,b in occ[round((y-4.32)/.27)] if b>row[1] and a<row[3]]+[(row[3],row[3])]
  for a,b in zip(intervals,intervals[1:]):
   lo=math.ceil((a[1]+.054-4.32)/.054)*.054+4.32
   hi=math.floor((b[0]-w-.054-4.32)/.054)*.054+4.32
   if lo>hi:continue
   x=max(lo,min(hi,round((tx-4.32)/.054)*.054+4.32))
   if abs(x-tx)>maxdx:continue
   d=abs(x-tx)+abs(y-ty)
   if best is None or d<best[0]:best=(d,round(x,3),round(y,3),r)
 if best is None:raise RuntimeError((tx,ty,w))
 return best
macros=[m[2:] for m in p['blocks']]
def cross(a,b,box):
 x,y,xx,yy=box
 if abs(a[0]-b[0])<1e-6:return x+1e-4<a[0]<xx-1e-4 and max(min(a[1],b[1]),y)<min(max(a[1],b[1]),yy)-1e-4
 return y+1e-4<a[1]<yy-1e-4 and max(min(a[0],b[0]),x)<min(max(a[0],b[0]),xx)-1e-4

def elbow(a,b):
 for c in [(a[0],b[1]),(b[0],a[1])]:
  if not any(cross(a,c,m) or cross(c,b,m) for m in macros):return c
 return None
# Slot planning honours existing standard-cell occupancy and 5um macro guard.
points={}
for x in range(10,301,35):
 for y in range(20,331,35):
  try:
   q=slot(x,y,1.62,maxdx=10,maxdy=8);v=(q[1]+.81,q[2]+.135);points[v]=q
  except RuntimeError:pass
N=defaultdict(list);P={}
for line in open(args.clocks):
 v=line.rstrip().split('\t');N[v[0]].append(v);P[v[1]+'/'+v[2]]=v
out={'basis':'actual vH 4CTS; TT clock placement RC; 5um cell guard; orthogonal path avoids macro bodies, not routed wire proof','rc_kohm_per_um':.0214161,'rc_ff_per_um':.113298,'stage_bound_ps':33.0749,'leaf_bound_ps':30.4546,'source_load_slope_ps_per_ff':.25,'plans':[]}
for bank,iso,goal in [(0,16,(37.212,25.962)),(2,14,(235.932,25.962))]:
 q=slot(goal[0]-.416,goal[1]-5.5,.648);leaf=(q[1]+.324,q[2]+.135)
 sources=[];v=P[f'ot_rt_etm_iso{iso}/A']
 for k in range(7):
  ds=[d for d in N[v[0]] if d[3]=='OUTPUT']
  if not ds:break
  d=ds[0];sources.append(d);v=P.get(d[1]+'/A')
  if not v:break
 for d in sources:
  src=tuple(map(float,d[4:6]));nodes=[src]+list(points)+[leaf];end=len(nodes)-1;dist={0:0};prev={};queue=[(0,0)]
  while queue:
   cost,i=heapq.heappop(queue)
   if cost!=dist[i]:continue
   if i==end:break
   for j,b in enumerate(nodes):
    if j==i or j==0:continue
    a=nodes[i];L=abs(a[0]-b[0])+abs(a[1]-b[1])
    if L>85 or elbow(a,b) is None:continue
    sink=.852045 if j==end else 2.35026;cap=.113298*L+sink
    if cap>23.04:continue
    rc=.0214161*L*(.113298*L/2+sink)
    nc=cost+rc+(.25*cap if i==0 else 33.0749)
    if nc<dist.get(j,1e20):dist[j]=nc;prev[j]=i;heapq.heappush(queue,(nc,j))
  if end not in dist:out['plans'].append({'bank':bank,'source':d[1],'status':'UNREACHABLE'});continue
  route=[];i=end
  while i:route.append(nodes[i]);i=prev[i]
  route.append(src);route.reverse();segments=[]
  for a,b in zip(route,route[1:]):
   L=abs(a[0]-b[0])+abs(a[1]-b[1]);segments.append({'length_um':round(L,3),'elbow':elbow(a,b),'wire_cap_ff':round(.113298*L,3)})
  LL=abs(leaf[0]-goal[0])+abs(leaf[1]-goal[1]);delay=dist[end]+30.4546+.0214161*LL*(.113298*LL/2+2.9406)
  out['plans'].append({'bank':bank,'source':d[1],'master':d[7],'status':'GEOMETRY_CANDIDATE','path_pin_centres_um':route,'leaf_bbox_xy':q[1:3],'segments':segments,'repeaters':len(route)-2,'estimated_extra_ps_20ps_input_slew':round(delay,3),'leaf_output_manhattan_um':round(LL,3),'qualification':'TT source arrival and loaded total/fanout must be evaluated; estimated physical topology only'})

if args.arrivals:
    arrivals={}
    for line in open(args.arrivals):
        name,rise,fall=line.rstrip().split('\t')
        arrivals[name]=float(rise)  # RF8 target uses arrival_max_rise; fall includes half-cycle phase
    for v in out['plans']:
        if v['source'] not in arrivals or v['status']!='GEOMETRY_CANDIDATE':continue
        v['actual_tt_source_arrival_ps']=arrivals[v['source']]
        v['estimated_tt_macro_arrival_ps']=round(arrivals[v['source']]+v['estimated_extra_ps_20ps_input_slew'],3)
        v['target_tt_macro_arrival_ps']={0:671.,2:673.}[v['bank']]
        v['estimated_target_error_ps']=round(v['estimated_tt_macro_arrival_ps']-v['target_tt_macro_arrival_ps'],3)
json.dump(out,open(args.output,'w'),indent=2)
